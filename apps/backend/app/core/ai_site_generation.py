"""
AI-native site generation - Phase 3 implementation.

Replaces deterministic section-by-section generation with a single AI pass
that produces complete landing page TSX code from the approved master brief.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
from app.core.compiler_client import CompilerError, get_compiler_client
from app.core.config import get_settings
from app.core.llm import get_llm_client
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)

MAX_COMPILATION_RETRIES = 3


def _upload_bundle_assets_to_s3(bundle_code: str, css_code: str | None, site_id: str) -> tuple[str, str | None]:
    """
    Upload compiled bundle to S3 and return public URL.

    Args:
        bundle_code: Compiled JavaScript bundle
        css_code: Optional CSS code
        site_id: Site identifier for path construction

    Returns:
        Public HTTPS URL to the bundle
    """
    settings = get_settings()
    s3_client = boto3.client(
        "s3",
        region_name=settings.asset_s3_region or "us-east-1",
    )

    bucket = settings.asset_s3_bucket
    if not bucket:
        logger.error("ASSET_S3_BUCKET not configured, cannot upload bundle")
        raise RuntimeError("S3 bucket not configured for bundle storage")

    # Generate S3 key path: bundles/<site_id>/bundle.js
    prefix = settings.asset_s3_prefix or "lenmanag/"
    bundle_key = f"{prefix}bundles/{site_id}/bundle.js"

    # Upload JS bundle
    s3_client.put_object(
        Bucket=bucket,
        Key=bundle_key,
        Body=bundle_code.encode("utf-8"),
        ContentType="application/javascript",
        CacheControl="public, max-age=3600",
    )

    # Upload CSS if present
    if css_code:
        css_key = f"{prefix}bundles/{site_id}/styles.css"
        s3_client.put_object(
            Bucket=bucket,
            Key=css_key,
            Body=css_code.encode("utf-8"),
            ContentType="text/css",
            CacheControl="public, max-age=3600",
        )

    # Generate public URL via backend proxy (includes CORS headers)
    # In production, this should be https://sites-api.lenquant.com
    # In development, this is http://localhost:8000
    import os

    api_base_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    bundle_url = f"{api_base_url}/api/v1/bundles/{site_id}/bundle.js"

    logger.info(f"Uploaded bundle for site {site_id} to S3, proxied URL: {bundle_url}")
    css_url = f"{api_base_url}/api/v1/bundles/{site_id}/styles.css" if css_code else None
    return bundle_url, css_url


def _upload_bundle_to_s3(bundle_code: str, css_code: str | None, site_id: str) -> str:
    return _upload_bundle_assets_to_s3(bundle_code, css_code, site_id)[0]


async def generate_landing_page_code(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    site_id: str,
    retry_context: dict[str, Any] | None = None,
    refinement_prompt: str | None = None,
) -> dict[str, Any]:
    """
    Generate complete TSX landing page code from master brief.

    Args:
        master_brief: Approved master brief
        extraction: Extraction snapshot for brand assets
        site_id: Site identifier
        retry_context: Optional context from previous failed attempt

    Returns:
        Dict with keys: sourceCode, compiledBundleUrl, compilationStatus, error
    """
    llm = get_llm_client()
    compiler = get_compiler_client()

    # Build generation prompt
    if retry_context:
        prompt = _build_correction_prompt(
            master_brief=master_brief,
            extraction=extraction,
            previous_code=retry_context["sourceCode"],
            error_message=retry_context["errorMessage"],
        )
    else:
        prompt = _build_generation_prompt(
            master_brief=master_brief,
            extraction=extraction,
            refinement_prompt=refinement_prompt,
        )

    # Generate code
    logger.info(f"Generating TSX code for site {site_id}")
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.8,  # Higher creativity for unique designs
        max_tokens=16_384,  # Bounded output keeps the model focused and avoids runaway truncation.
    )

    # Extract code from response
    source_code = _extract_tsx_code(response)

    # Validate syntax — retry with feedback if validation fails
    validation_errors = _validate_tsx_source(source_code)
    if validation_errors:
        logger.warning(f"TSX validation errors on first attempt: {validation_errors}")
        source_code = await _retry_generation_with_validation_feedback(
            llm=llm,
            original_code=source_code,
            validation_errors=validation_errors,
            master_brief=master_brief,
            extraction=extraction,
        )
        # Re-validate after retry
        final_errors = _validate_tsx_source(source_code)
        if final_errors:
            logger.error(f"TSX validation still failing after retry: {final_errors}")
            return {
                "success": False,
                "sourceCode": source_code,
                "compilationStatus": "validation_failed",
                "validationErrors": final_errors,
                "error": f"Code validation failed after retry: {', '.join(final_errors[:3])}",
            }

    # Compile code
    logger.info(f"Compiling TSX code for site {site_id}")
    try:
        compile_result = await compiler.compile_tsx(
            source_code=source_code,
            component_name=f"LandingPage_{site_id}",
            site_id=site_id,
        )

        if compile_result.get("success"):
            # Upload compiled bundle to S3
            bundle_code = compile_result.get("bundleCode")
            css_code = compile_result.get("cssCode")

            if not bundle_code:
                return {
                    "success": False,
                    "sourceCode": source_code,
                    "compilationStatus": "compilation_failed",
                    "error": "Compilation succeeded but no bundle code returned",
                }

            try:
                bundle_url, css_url = _upload_bundle_assets_to_s3(bundle_code, css_code, site_id)
            except Exception as upload_error:
                logger.error(
                    f"Failed to upload bundle for site {site_id}: {upload_error}"
                )
                return {
                    "success": False,
                    "sourceCode": source_code,
                    "compilationStatus": "upload_failed",
                    "error": f"Bundle upload failed: {str(upload_error)}",
                }

            return {
                "success": True,
                "sourceCode": source_code,
                "compiledBundleUrl": bundle_url,
                "compiledCssUrl": css_url,
                "compilationStatus": "success",
                "bundleCode": bundle_code,
                "cssCode": css_code,
            }
        else:
            return {
                "success": False,
                "sourceCode": source_code,
                "compilationStatus": "compilation_failed",
                "validationErrors": compile_result.get("validationErrors", []),
                "error": compile_result.get("error", "Unknown compilation error"),
            }

    except CompilerError as e:
        logger.error(f"Compilation error for site {site_id}: {e}")
        return {
            "success": False,
            "sourceCode": source_code,
            "compilationStatus": "compiler_error",
            "error": str(e),
        }


def _build_generation_prompt(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    refinement_prompt: str | None = None,
) -> str:
    """Build the main generation prompt — leads with inspiration, not restrictions."""
    # Extract brand tokens
    brand_section = _build_brand_tokens_section(master_brief, extraction)

    # Proof is opt-in. Auto-approved briefs may intentionally have no verified
    # testimonials, reviews, ratings, awards, or customer metrics. Keep those
    # sections out of the generation context so the model is not encouraged to
    # fill a content gap with plausible-looking fiction.
    extracted_content = getattr(master_brief, "extractedContent", {}) or {}
    approved_testimonials = [
        str(value).strip()
        for value in (extracted_content.get("testimonials", []) or [])
        if str(value).strip()
    ]
    proof_allowed = bool(approved_testimonials)
    proof_terms = re.compile(
        r"testimonial|review|rating|social[- ]proof|customer quote|what clients say|award|badge|results?",
        re.I,
    )
    eligible_sections = [
        section
        for section in master_brief.sections
        if proof_allowed or not proof_terms.search(
            " ".join(
                (
                    str(getattr(section, "purpose", "")),
                    str(getattr(section, "headline", "")),
                    str(getattr(section, "contentSummary", "")),
                    str(getattr(section, "suggestedApproach", "")),
                )
            )
        )
    ]

    # Extract content sections
    sections_list = "\n".join(
        [
            f"  {i + 1}. **{section.headline}** ({section.purpose})\n"
            f"     Approach: {section.suggestedApproach}\n"
            f"     Content: {section.contentSummary}\n"
            f"     Key points (all approved): {', '.join(section.contentPoints)}"
            for i, section in enumerate(eligible_sections)
        ]
    )
    if not sections_list:
        sections_list = "  1. Use the hero and primary conversion action only."
    proof_context = (
        "\n".join(f'  - Approved testimonial: "{quote}"' for quote in approved_testimonials[:8])
        if proof_allowed
        else "  - None approved. Omit testimonials, reviews, ratings, awards, customer quotes, result metrics, and proof-like badges entirely."
    )

    # Build creative direction section if available
    creative_section = ""
    if hasattr(master_brief, "creativeDirection") and master_brief.creativeDirection:
        cd = master_brief.creativeDirection
        micro_interactions = (
            chr(10).join(f"  - {mi}" for mi in cd.microInteractions)
            if cd.microInteractions
            else "  - Smooth scroll-triggered reveals"
        )
        inspiration = (
            ", ".join(cd.inspirationKeywords)
            if cd.inspirationKeywords
            else "modern, premium, engaging"
        )
        avoid = (
            ", ".join(cd.avoidPatterns)
            if cd.avoidPatterns
            else "generic templates, centered-everything"
        )
        creative_section = f"""
## CREATIVE DIRECTION (THIS IS YOUR NORTH STAR)

**Design Concept**: {cd.designConcept}
**Hero Treatment**: {cd.heroTreatment}
**Signature Technique**: {cd.signatureTechnique} — THIS is what makes this site memorable. IMPLEMENT IT.
**Layout Strategy**: {cd.layoutStrategy}
**Scroll Behavior**: {cd.scrollBehavior}
**Color Mood**: {cd.colorMood}
**Typography Personality**: {cd.typographyPersonality}

**Micro-interactions to implement**:
{micro_interactions}

**Inspiration keywords**: {inspiration}

**AVOID these patterns**: {avoid}
"""

    # Build design mode guidance if available
    design_mode_guidance = ""
    if hasattr(master_brief, "designMode") and master_brief.designMode:
        mode_details = {
            "editorial": """
**EDITORIAL MODE**: Think magazine spread. Heavy typography moments. Asymmetric layouts.
Mixed font sizes (huge headlines, small captions). Image/text juxtaposition. Generous whitespace.
- Use text-8xl or larger for key headlines
- Mix serif and sans-serif for contrast
- Remember to give proper space btw contents/arts and use paddings approprietaly
- Use approved client images first; if none are suitable, use CSS/typography/texture instead of random stock photography.
- Consider pull quotes, drop caps, full-bleed images
- Sections should feel like turning pages""",
            "immersive": """
**IMMERSIVE MODE**: Think cinematic experience. Full-bleed everything. Parallax depth layers.
Ambient backgrounds (gradients, particles, video). Story-driven scroll progression.
- Use useScroll + useTransform extensively for parallax
- Consider CSS/SVG ambient backgrounds and layered depth
- Sections should flow like a film, not a document
- Sound/motion cues (even if just visual representations)""",
            "interactive": """
**INTERACTIVE MODE**: Make everything respond. Cursor effects - if you find necessary). Hover transformations.
Click feedback. Scroll-triggered reveals everywhere. Gamified elements.
- Every card should have a hover state with transform
- Consider magnetic buttons, cursor trails
- Text should reveal on scroll with stagger
- Add micro-celebrations (confetti, pulses, glows)""",
            "minimalist": """
**MINIMALIST MODE**: Less is more, but what's there is BOLD. Dramatic whitespace.
Few colors. High contrast. Typography as architecture.
- Limit to 2-3 colors max
- Use scale contrast (tiny vs huge)
- Generous padding and margins
- Let elements breathe — avoid cramped layouts""",
            "playful": """
**PLAYFUL MODE**: Personality first. Organic shapes. Bouncy spring animations.
Vibrant colors. Unexpected layouts. Fun > formal.
- Use spring physics in framer-motion
- Consider blob shapes, wavy dividers
- Bright, saturated colors
- Quirky micro-copy and CTAs""",
            "corporate": """
**CORPORATE MODE**: Professional polish, not boring. Structured grids with life.
Subtle motion. Trust signals. Refined color usage.
- Clean grid layouts but with visual interest
- Subtle hover states and transitions
- Establish trust with accurate service details, clear process, and source-backed claims; never invent proof
- Motion should feel confident, not flashy""",
        }
        design_mode_guidance = mode_details.get(master_brief.designMode, "")

    prompt = f"""You are building an Awwwards-worthy landing page. Your goal is to create something memorable — not a template, but an experience.

## PRIORITY ORDER
1. Use only accurate client facts and approved content.
2. Use the exact approved logo, structured brand colors, typography, and imagery.
3. Transform those assets into an art-directed redesign with one memorable signature moment.
4. Ensure responsive and runtime reliability.

Do not copy the source layout or default to a generic SaaS template. Choose one coherent concept and one or two excellent signature effects. Creative risk is encouraged for this sales concept, but it must fit this client and cannot depend on unavailable libraries.

## YOUR CREATIVE TOOLKIT

You have access to powerful libraries. YOU CAN USE THEM OR SOME OF THEM CREATIVELY, OR NOT AT ALL. The choice is yours, but the final product must be visually stunning and interactive.:

### Animation & Motion
- **framer-motion**: motion.div, useScroll, useTransform, useInView, AnimatePresence, variants, stagger
  - Parallax: `useTransform(scrollYProgress, [0, 1], [0, -200])`
  - Scroll-triggered reveals: `initial={{{{ opacity: 0, y: 50 }}}} whileInView={{{{ opacity: 1, y: 0 }}}} viewport={{{{ once: true, amount: 0.1 }}}} transition={{{{ duration: 0.6 }}}}`
  - **CRITICAL**: ALWAYS include `viewport={{{{ once: true, amount: 0.1 }}}}` on every `whileInView` element — without it, elements that start in the viewport will stay at opacity:0 forever
  - Elements visible on page load (hero, above-fold content): use `animate` instead of `whileInView` — `animate={{{{ opacity: 1, y: 0 }}}}` with `initial={{{{ opacity: 0, y: 20 }}}}`
  - Stagger children: `transition={{{{ staggerChildren: 0.1 }}}}`
  - Magnetic effect: track mouse position, apply transform toward cursor

- **GSAP + ScrollTrigger**: For complex timelines and scroll-driven animations
  - Pin sections while content animates
  - Scrub animations tied to scroll position
  - Split text animations

- **Lenis**: Smooth scrolling that makes the whole page feel premium

### 3D & Visual Effects
3D packages are not available in the preview compiler; create depth with CSS, SVG, gradients, and layered composition instead.

### UI Components (only these virtual shadcn components are available)
Import from '@/components/ui/*':
- Button, Card, Badge, Separator

### Images & Videos
- Use approved extracted images by role; do not use random stock imagery.

### Icons
- **lucide-react**: 1000+ icons — Menu, X, ArrowRight, ArrowUpRight, Check, Star, Phone, Mail, MapPin, Play, Pause, ChevronDown, ExternalLink, etc.

### Carousel
- **embla-carousel-react**: Smooth, accessible carousels

{creative_section}
{design_mode_guidance}

## MASTER BRIEF

**Business Goal**: {master_brief.businessGoal}
**Target Audience**: {master_brief.primaryAudience}
**Value Proposition**: {master_brief.valueProposition}
**Conversion Action**: {master_brief.conversionAction}
**Tone & Voice**: {master_brief.toneAndVoice}

**Visual Direction**:
- Style: {master_brief.visualStyle}
- Color Strategy: {master_brief.colorStrategy}
- Motion Level: {master_brief.motionLevel}
- Special Effects: {", ".join(master_brief.specialEffects) if master_brief.specialEffects else "None specified"}

**Hero**:
- Headline: {master_brief.headline}
- Subheadline: {master_brief.subheadline}

**Page Sections**:
{sections_list}

**CTA Strategy**: {master_brief.ctaStrategy}

## PROOF AND CLAIMS CONTRACT (NON-NEGOTIABLE)
{proof_context}
- Use only the approved proof text above, verbatim, and do not add names, companies, ratings, awards, metrics, review counts, or trust badges that are not present there.
- If the approved list says none, do not create an empty proof section or replace it with invented “results”, logos, stars, badges, or customer language. Omit it and strengthen the real service/process/content sections instead.

{brand_section}

## DESIGN PATTERNS/EXAMPLES TO CONSIDER OR BE CREATIVE: Combining patterns in a unique way

**Hero Patterns**:
- Split-screen: video/3D left, text right (or reversed)
- Oversized kinetic typography with scroll-reveal
- Bento grid hero with multiple interactive cards
- Full-bleed with floating elements and parallax layers
- Gradient mesh or particle background with centered content

**Section Patterns**:
- Bento grids with varied card sizes (not uniform 3-column)
- Alternating image/text with scroll-triggered reveals
- Horizontal scroll galleries for features or testimonials
- Sticky headers with scrolling content
- Cards with 3D tilt on hover (transform: perspective + rotateX/Y)
- Overlapping sections with negative margins

**Micro-interactions**:
- Magnetic buttons: track mouse, apply subtle transform toward cursor
- Card tilt: `transform: perspective(1000px) rotateX(${{tiltY}}deg) rotateY(${{tiltX}}deg)`
- Text reveals: `overflow-hidden` parent with `translateY(100%)` to `translateY(0)` child
- Parallax layers: different `useTransform` multipliers for foreground/background
- Hover state transitions: scale, shadow depth, color shifts

**Typography**:
- Display headlines: `text-6xl md:text-8xl lg:text-9xl font-bold tracking-tight`
- Gradient text: `bg-gradient-to-r from-X to-Y bg-clip-text text-transparent`
- Mixed weights: bold headlines, light body
- Letter-spacing: tight for headlines (-0.02em), normal for body

**Spacing & Breathability**:
- Content should have comfortable breathing room — avoid text glued to card/container edges
- Minimum 16px padding inside cards and containers (use px-2 py-2 md:px-2 md:py-2 or higher)
- Use whitespace intentionally to create visual hierarchy
- Sections should have generous vertical spacing (py-12 md:py-16 lg:py-24)

## OUTPUT REQUIREMENTS

1. Export a single default React component
2. Use TypeScript/TSX with proper types
3. Use Tailwind CSS for styling (including arbitrary values like `text-[120px]`)
4. Mobile responsive: sm:, md:, lg:, xl: breakpoints
5. All content from the brief — NO placeholder text
6. Implement the signature technique from creative direction
7. Match the motion level: "{master_brief.motionLevel}"
8. Responsive images: Always constrain images with max-width: 100%, object-fit: cover, and appropriate containers to prevent layout breaks
9. **ANIMATION VISIBILITY RULE**: Every `motion.*` element with `initial={{{{ opacity: 0 }}}}` MUST become visible. Use `animate` (not `whileInView`) for above-fold/hero elements. Use `whileInView` with `viewport={{{{ once: true, amount: 0.1 }}}}` for below-fold elements. NEVER leave an element at opacity:0 permanently.
10. Keep the complete component concise enough to finish in one response: target under 3,500 lines and under 12,000 generated tokens. Prefer reusable arrays, compact CSS classes, and a small number of polished sections over duplicated markup. Never stop mid-tag, mid-string, or mid-expression.
11. HARD COPY RULE: avoid em dash (—) and en dash (–) characters in generated copy. Use an ASCII hyphen (-) or rewrite the sentence before returning the component.

## BROWSER-ONLY CONSTRAINTS

This runs in the browser, NOT Node.js:
- NO fs, path, child_process, os, crypto, buffer, stream, net, http, https, url, util imports
- NO __dirname, __filename, process.env, require(), module.exports
- NO eval() or new Function()
- Images: use URLs from brand assets or leave empty — NEVER filesystem paths like ./image.png
- Cursor: Maintain default browser cursor unless implementing custom cursor (never use cursor: none without replacement)

## CODE REQUIREMENTS

- Start with `'use client';`
- Export a single default function component
- Import only what you actually use
- Available imports: `react`, `framer-motion`, `gsap`, `gsap/ScrollTrigger`, `lenis`, `lucide-react`, `embla-carousel-react`, and `@/components/ui/{{button,card,badge,separator}}` only.

## OUTPUT

Return ONLY the complete TSX code. No markdown code fences, no explanations.
Start with `'use client';` and end with the closing brace of the component.

**UNIQUENESS REQUIREMENT**: This output must be visually unlike any other landing page generated from this brief. If this prompt were run 10 times, this result should look completely different from the other 9. Surprise yourself — commit fully to the creative direction, don't hedge toward a safe layout.
"""

    if refinement_prompt:
        prompt += f"""

## Operator Refinement Instructions

The operator reviewed the previous version and provided this feedback. You MUST incorporate these changes — they take priority over any default creative direction:

{refinement_prompt}
"""

    return prompt


def _build_correction_prompt(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,  # noqa: ARG001
    previous_code: str,
    error_message: str,
) -> str:
    """Build correction prompt for failed compilation.

    Handles both syntax/validation errors and truncation issues.
    Preserves creative intent from the original generation.
    """
    # Build creative direction reminder if available
    creative_reminder = ""
    if hasattr(master_brief, "creativeDirection") and master_brief.creativeDirection:
        cd = master_brief.creativeDirection
        creative_reminder = f"""
## PRESERVE CREATIVE INTENT
When fixing errors, maintain the creative direction:
- **Signature Technique**: {cd.signatureTechnique} — Keep this effect!
- **Design Concept**: {cd.designConcept}
- **Hero Treatment**: {cd.heroTreatment}
Do NOT simplify or remove creative elements just to fix errors.
"""

    # Detect truncation issues
    is_likely_truncated = (
        "Unexpected end of file" in error_message
        or "Expected '>' but found end of file" in error_message
        or "closing tag" in error_message.lower()
        or len(previous_code) < 2000  # Very short code is suspicious
    )

    if is_likely_truncated:
        prompt = f"""CRITICAL: Your previous landing page code was TRUNCATED (incomplete).

## The Problem
{error_message}

The code you generated was cut off before completion. This is a CRITICAL issue.
{creative_reminder}

## What You Must Do
Generate a COMPLETE landing page with ALL sections FULLY closed:
1. Start with proper imports
2. Build the complete component with ALL sections from the master brief
3. **ENSURE every opening tag has a matching closing tag**
4. **ENSURE the component's return statement is fully complete**
5. **ENSURE the component function closes properly**
6. End with the closing braces

## Master Brief Requirements
**Sections to include** (ALL must be complete):
{chr(10).join(f"  - {section.headline}" for section in master_brief.sections[:10])}

## Previous Code (INCOMPLETE - DO NOT REPEAT THIS)
```tsx
{previous_code[:1000]}
... [TRUNCATED]
```

## Instructions
1. Generate COMPLETE code that includes ALL sections
2. Do NOT truncate or abbreviate - write the full implementation
3. Test each section is properly closed before moving to the next
4. Return ONLY the complete TSX code, no markdown fences
5. Make sure to close ALL tags before ending the response
6. Keep all creative animations and effects from the previous attempt

GENERATE THE COMPLETE CODE NOW:
"""
    else:
        prompt = f"""The landing page code you generated has compilation errors. Please fix them.

## Error Message
{error_message}
{creative_reminder}

## Previous Code
```tsx
{previous_code[:8000]}
```

## Instructions
1. Analyze the error message carefully
2. Fix the specific issues (syntax errors, import problems, type errors)
3. **Keep the same creative design, animations, and visual effects**
4. Return ONLY the corrected TSX code, no markdown or explanations

## Common Issues to Check
- Missing imports
- Incorrect component syntax
- Type errors
- Invalid JSX structure
- Using unavailable libraries
- Node.js modules (fs, path, etc.) - NEVER use these
- Unclosed tags or components

**Remember**: Fix the errors but preserve the creative elements (animations, micro-interactions, unique layouts).

Return the corrected TSX code now:
"""
    return prompt


def _build_brand_tokens_section(
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,  # noqa: ARG001
) -> str:
    """Build brand tokens section for the prompt."""
    sections = []

    # Colors
    if master_brief.brandAssets.primaryColor:
        sections.append(
            f"**Primary Color**: {master_brief.brandAssets.primaryColor} — Use this as your palette foundation (can generate complementary shades, but this should be dominant in buttons, links, and key accents)"
        )
    if master_brief.brandAssets.secondaryColor:
        sections.append(
            f"**Secondary Color**: {master_brief.brandAssets.secondaryColor} — Use in accent areas and to complement the primary color"
        )

    # Logo
    if master_brief.brandAssets.logoUrl:
        sections.append(
            f"**Logo**: {master_brief.brandAssets.logoUrl} — Use this exact logo in your site header"
        )

    # Typography
    if master_brief.brandAssets.fontFamily:
        sections.append(
            f"**Font Family**: {master_brief.brandAssets.fontFamily} — Apply this font throughout the design"
        )
    if master_brief.brandAssets.fontUrl:
        sections.append(
            f"**Font File**: {master_brief.brandAssets.fontUrl} (weight {master_brief.brandAssets.fontWeight or '400'}) — load with @font-face and provide a compatible fallback"
        )

    # Images
    if master_brief.brandAssets.imageUrls:
        image_list = "\n  ".join(
            [f"- {url}" for url in master_brief.brandAssets.imageUrls[:5]]
        )
        sections.append(
            f"**Available Images** (use responsively with max-width: 100% and object-fit: cover):\n  {image_list}"
        )

    if not sections:
        return "**Brand Assets**: No approved assets were extracted; use a restrained inferred palette and never invent a logo."

    return "## Brand Assets (USE THESE)\n\n" + "\n".join(sections)


def _extract_tsx_code(response: str) -> str:
    """Extract TSX code from LLM response, removing markdown formatting."""
    # Remove markdown code fences
    code = response.strip()

    # Remove ```tsx or ```typescript markers
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (opening fence)
        lines = lines[1:]
        # Remove last line if it's a closing fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    return code.strip()


def _extract_html_code(response: str) -> str:
    """Extract HTML code from LLM response, removing markdown formatting."""
    code = response.strip()

    # Remove ```html or ```HTML markers
    if code.startswith("```"):
        lines = code.split("\n")
        lines = lines[1:]  # Remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove closing fence
        code = "\n".join(lines)

    return code.strip()


async def _retry_generation_with_validation_feedback(
    *,
    llm: Any,
    original_code: str,
    validation_errors: list[str],
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,  # noqa: ARG001
    max_retries: int = 2,
) -> str:
    """
    Retry code generation with validation error feedback.

    Sends the LLM the original code with specific validation errors
    and asks it to fix the issues while keeping the same design and creative direction.
    """
    errors_text = "\n".join(f"  - {error}" for error in validation_errors)

    # Build creative direction reminder if available
    creative_reminder = ""
    if hasattr(master_brief, "creativeDirection") and master_brief.creativeDirection:
        cd = master_brief.creativeDirection
        creative_reminder = f"""
## PRESERVE CREATIVE DIRECTION
When fixing errors, maintain these creative elements:
- **Signature Technique**: {cd.signatureTechnique}
- **Design Concept**: {cd.designConcept}
- **Micro-interactions**: {", ".join(cd.microInteractions[:3]) if cd.microInteractions else "scroll reveals, hover effects"}
Do NOT simplify or remove animations/effects just to fix validation errors.
"""

    for attempt in range(max_retries):
        logger.info(
            "Validation retry attempt %d/%d for code generation",
            attempt + 1,
            max_retries,
        )

        feedback_prompt = f"""Your previously generated React landing page component was REJECTED due to validation errors.

## VALIDATION ERRORS (must fix ALL of these):
{errors_text}
{creative_reminder}

## CRITICAL RULES — BROWSER-ONLY CODE:
- This is a React component that runs in the BROWSER, NOT Node.js
- DO NOT import or use ANY Node.js built-in modules: fs, path, child_process, os, crypto, buffer, stream, net, http, https, url, util
- DO NOT use: __dirname, __filename, process.env, require(), module.exports
- DO NOT use: eval(), new Function(), or any dynamic code execution
- DO NOT use filesystem operations of any kind
- All data must be hardcoded from the brief content or come from React state
- Images must use URLs (https://...) or data URIs, NEVER filesystem paths

## ALLOWED IMPORTS ONLY:
- React and hooks from 'react'
- framer-motion for animations (motion.div, useScroll, useTransform, useInView, AnimatePresence)
- GSAP and ScrollTrigger
- CSS/SVG depth effects (React Three Fiber and Drei are not available)
- Lenis for smooth scrolling
- shadcn/ui components from '@/components/ui/*'
- Lucide React icons from 'lucide-react'
- embla-carousel-react

## PREVIOUS CODE (with errors):
```tsx
{original_code[:6000]}
```

## INSTRUCTIONS:
1. Fix ALL validation errors listed above
2. **Keep the same creative design, animations, micro-interactions, and visual effects**
3. Remove any Node.js imports (fs, path, etc.) and replace with browser-safe alternatives
4. Return ONLY the corrected TSX code — no markdown fences, no explanations
5. Preserve the Awwwards-worthy quality of the design
"""

        response = await llm.generate_text(
            prompt=feedback_prompt,
            temperature=0.5,
            max_tokens=16_384,
        )

        fixed_code = _extract_tsx_code(response)
        new_errors = _validate_tsx_source(fixed_code)

        if not new_errors:
            logger.info("Validation retry succeeded on attempt %d", attempt + 1)
            return fixed_code

        logger.warning(
            "Validation retry %d still has errors: %s",
            attempt + 1,
            new_errors[:3],
        )
        original_code = fixed_code
        errors_text = "\n".join(f"  - {error}" for error in new_errors)

    return original_code


def _validate_tsx_source(source_code: str) -> list[str]:
    """
    Validate generated TSX source code for safety and correctness.

    Returns list of validation errors, empty list if valid.
    """
    errors = []

    if re.search(r"\b(?:arial|comic\s+sans(?:\s+ms)?)\b", source_code, re.I):
        errors.append("Prohibited basic Windows font detected")
    if re.search(r"\b(?:lorem ipsum|example\.com|todo|xxx|coming soon|contact us for details|image placeholder)\b", source_code, re.I):
        errors.append("Placeholder content detected")
    if re.search(r"(?:src|href)\s*=\s*['\"]http://|url\(\s*['\"]?http://", source_code, re.I):
        errors.append("Insecure HTTP asset URL detected")

    # Check for dangerous Node.js imports/patterns
    dangerous_patterns = [
        ("import fs", "File system import not allowed (Node.js module)"),
        ("from 'fs'", "File system import not allowed (Node.js module)"),
        ("require('fs')", "File system require not allowed (Node.js module)"),
        ('from "fs"', "File system import not allowed (Node.js module)"),
        ("import path", "Path module import not allowed (Node.js module)"),
        ("from 'path'", "Path module import not allowed (Node.js module)"),
        ('from "path"', "Path module import not allowed (Node.js module)"),
        ("child_process", "Process spawning not allowed (Node.js module)"),
        ("from 'os'", "OS module not allowed (Node.js module)"),
        ('from "os"', "OS module not allowed (Node.js module)"),
        ("from 'crypto'", "Crypto module not allowed (Node.js module)"),
        ('from "crypto"', "Crypto module not allowed (Node.js module)"),
        ("from 'buffer'", "Buffer module not allowed (Node.js module)"),
        ('from "buffer"', "Buffer module not allowed (Node.js module)"),
        ("from 'stream'", "Stream module not allowed (Node.js module)"),
        ('from "stream"', "Stream module not allowed (Node.js module)"),
        ("eval(", "eval() not allowed — dynamic code execution is forbidden"),
        (
            "new Function(",
            "Function constructor not allowed — dynamic code execution is forbidden",
        ),
        ("__dirname", "Node.js path global not allowed (browser-only code)"),
        ("__filename", "Node.js path global not allowed (browser-only code)"),
        ("process.env", "process.env not allowed (browser-only code)"),
        ("require(", "require() not allowed — use ES module imports only"),
        ("module.exports", "module.exports not allowed — use ES module exports only"),
        ("readFileSync", "Filesystem operations not allowed"),
        ("writeFileSync", "Filesystem operations not allowed"),
        ("readFile(", "Filesystem operations not allowed"),
        ("writeFile(", "Filesystem operations not allowed"),
    ]

    for pattern, message in dangerous_patterns:
        if pattern in source_code:
            lines = source_code.split("\n")
            matching_lines = [
                f"Line {i + 1}: {line.strip()}"
                for i, line in enumerate(lines)
                if pattern in line
            ]
            error_detail = f"{message} (found in: {'; '.join(matching_lines[:3])})"
            errors.append(error_detail)
            logger.error("TSX validation error: %s", error_detail)

    # Check for export
    if "export default" not in source_code:
        errors.append("Must export a default component")

    # Check minimum structure
    if "return" not in source_code:
        errors.append("Component must have a return statement")

    # Check for basic React structure
    if "React" not in source_code and "from 'react'" not in source_code:
        errors.append("Must import React")

    return errors


def _build_refinement_prompt(
    *, current_source_code: str, refinement_prompt: str, is_html: bool = False
) -> str:
    """Build a prompt for targeted in-place edits to existing generated code."""
    if is_html:
        return f"""You are editing an existing HTML landing page. Apply the requested changes precisely and return the complete modified code.

## Existing Code
```html
{current_source_code}
```

## Operator Instructions (apply these changes ONLY)
{refinement_prompt}

## Rules
- Apply ONLY the requested changes — do not redesign, restructure, or alter anything not mentioned
- Preserve all styles, scripts, animations, and layout that are not being changed
- Do NOT add, remove, or reorder sections unless explicitly asked
- Return ONLY the complete modified HTML — no markdown fences, no explanations
- Start with `<!DOCTYPE html>` and include the full document
"""
    return f"""You are editing an existing React landing page component. Apply the requested changes precisely and return the complete modified code.

## Existing Code
```tsx
{current_source_code}
```

## Operator Instructions (apply these changes ONLY)
{refinement_prompt}

## Rules
- Apply ONLY the requested changes — do not redesign, restructure, or alter anything not mentioned
- Preserve all animations, interactions, layout, and creative elements that are not being changed
- Keep the same imports, component structure, and TypeScript types
- Do NOT add, remove, or reorder sections unless explicitly asked
- Return ONLY the complete modified TSX code — no markdown fences, no explanations
- Start with `'use client';` and end with the closing brace of the component
"""


async def refine_landing_page_code(
    *,
    site_id: str,
    current_source_code: str,
    refinement_prompt: str,
    variant_type: str = "nextjs",
) -> dict[str, Any]:
    """Apply targeted operator edits to existing generated code without full regeneration."""
    llm = get_llm_client()
    compiler = get_compiler_client()

    _stripped = current_source_code.lstrip()
    # Strip 'use client'; directive before checking for HTML — some sites have it prepended
    if _stripped.startswith(("'use client'", '"use client"')):
        _stripped = _stripped.split("\n", 1)[-1].lstrip()
    is_html_variant = variant_type.startswith("html_") or _stripped.startswith(
        ("<!DOCTYPE", "<html", "<!doctype")
    )

    prompt = _build_refinement_prompt(
        current_source_code=current_source_code,
        refinement_prompt=refinement_prompt,
        is_html=is_html_variant,
    )

    logger.info(f"Refining {variant_type} code for site {site_id}")
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.3,
        max_tokens=16_384,
    )

    source_code = (
        _extract_tsx_code(response)
        if not is_html_variant
        else _extract_html_code(response)
    )

    # Only validate TSX for Next.js sites, skip for HTML variants
    if not is_html_variant:
        validation_errors = _validate_tsx_source(source_code)
        if validation_errors:
            logger.warning(
                f"TSX validation errors on refinement attempt: {validation_errors}"
            )
            return {
                "success": False,
                "sourceCode": source_code,
                "compilationStatus": "validation_failed",
                "validationErrors": validation_errors,
                "error": f"Code validation failed: {', '.join(validation_errors[:3])}",
            }

    # For HTML variants, skip compilation and return immediately
    if is_html_variant:
        logger.info(
            f"HTML variant {variant_type} refined successfully for site {site_id}"
        )
        return {
            "success": True,
            "sourceCode": source_code,
            "compilationStatus": "success",
            "staticHtml": source_code,
        }

    logger.info(f"Compiling refined TSX code for site {site_id}")
    try:
        compile_result = await compiler.compile_tsx(
            source_code=source_code,
            component_name=f"LandingPage_{site_id}",
            site_id=site_id,
        )

        if compile_result.get("success"):
            bundle_code = compile_result.get("bundleCode")
            css_code = compile_result.get("cssCode")

            if not bundle_code:
                return {
                    "success": False,
                    "sourceCode": source_code,
                    "compilationStatus": "compilation_failed",
                    "error": "Compilation succeeded but no bundle code returned",
                }

            try:
                bundle_url, css_url = _upload_bundle_assets_to_s3(bundle_code, css_code, site_id)
            except Exception as upload_error:
                logger.error(
                    f"Failed to upload refined bundle for site {site_id}: {upload_error}"
                )
                return {
                    "success": False,
                    "sourceCode": source_code,
                    "compilationStatus": "upload_failed",
                    "error": f"Bundle upload failed: {str(upload_error)}",
                }

            return {
                "success": True,
                "sourceCode": source_code,
                "compiledBundleUrl": bundle_url,
                "compiledCssUrl": css_url,
                "compilationStatus": "success",
                "bundleCode": bundle_code,
                "cssCode": css_code,
            }
        else:
            return {
                "success": False,
                "sourceCode": source_code,
                "compilationStatus": "compilation_failed",
                "validationErrors": compile_result.get("validationErrors", []),
                "error": compile_result.get("error", "Unknown compilation error"),
            }

    except CompilerError as e:
        logger.error(f"Compilation error during refinement for site {site_id}: {e}")
        return {
            "success": False,
            "sourceCode": source_code,
            "compilationStatus": "compiler_error",
            "error": str(e),
        }


async def refine_with_retry(
    *,
    site_id: str,
    current_source_code: str,
    refinement_prompt: str,
    variant_type: str = "nextjs",
    max_retries: int = MAX_COMPILATION_RETRIES,
) -> dict[str, Any]:
    """Refine landing page code with retry on compilation failure."""
    result: dict[str, Any] = {
        "success": False,
        "compilationStatus": "not_attempted",
        "error": "No attempts made",
    }

    for attempt in range(max_retries):
        logger.info(
            f"Refinement attempt {attempt + 1}/{max_retries} for site {site_id}"
        )

        result = await refine_landing_page_code(
            site_id=site_id,
            current_source_code=current_source_code,
            refinement_prompt=refinement_prompt,
            variant_type=variant_type,
        )

        if result["success"]:
            logger.info(f"Successfully refined site {site_id} on attempt {attempt + 1}")
            return result

        compilation_status = result.get("compilationStatus", "unknown")
        error_message = result.get("error", "Unknown error")
        logger.warning(
            f"Refinement attempt {attempt + 1} failed for site {site_id}: "
            f"status={compilation_status}, error={error_message[:200]}"
        )

        if compilation_status not in (
            "compilation_failed",
            "compiler_error",
            "validation_failed",
        ):
            break

        # On compilation failure, retry with the corrected source using the same refinement intent
        current_source_code = result.get("sourceCode", current_source_code)

    logger.error(f"All {max_retries} refinement attempts failed for site {site_id}")
    return {
        "success": False,
        "compilationStatus": "retries_exhausted",
        "error": f"Failed after {max_retries} attempts: {result.get('error', 'Unknown')}",
        "finalAttemptResult": result,
    }


async def generate_with_retry(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    site_id: str,
    max_retries: int = MAX_COMPILATION_RETRIES,
    refinement_prompt: str | None = None,
) -> dict[str, Any]:
    """
    Generate landing page code with automatic retry on compilation failure.

    Handles both validation errors and compilation errors (422) by:
    1. First attempt: Generate fresh code
    2. On failure: Use correction prompt with error details
    3. Retry up to max_retries times with correction context

    Returns final result after retries.
    """
    retry_context = None
    result: dict[str, Any] = {
        "success": False,
        "compilationStatus": "not_attempted",
        "error": "No attempts made",
    }

    for attempt in range(max_retries):
        logger.info(
            f"Generation attempt {attempt + 1}/{max_retries} for site {site_id}"
        )

        result = await generate_landing_page_code(
            master_brief=master_brief,
            extraction=extraction,
            site_id=site_id,
            retry_context=retry_context,
            refinement_prompt=refinement_prompt,
        )

        if result["success"]:
            logger.info(
                f"Successfully generated site {site_id} on attempt {attempt + 1}"
            )
            return result

        # Log failure details
        compilation_status = result.get("compilationStatus", "unknown")
        error_message = result.get("error", "Unknown error")

        logger.warning(
            f"Attempt {attempt + 1} failed for site {site_id}:\n"
            f"  Status: {compilation_status}\n"
            f"  Error: {error_message[:200]}"
        )

        # Check if this is a compilation error (422) or validation error
        # Both should trigger correction prompt
        if compilation_status in (
            "compilation_failed",
            "compiler_error",
            "validation_failed",
        ):
            # Prepare retry context with full error details
            retry_context = {
                "sourceCode": result.get("sourceCode", ""),
                "errorMessage": error_message,
                "compilationStatus": compilation_status,
                "validationErrors": result.get("validationErrors", []),
                "attempt": attempt + 1,
            }
            logger.info(
                "Will retry with correction prompt (compilation/validation error detected)"
            )
        else:
            # For other errors (network, timeout, etc.), prepare basic retry context
            retry_context = {
                "sourceCode": result.get("sourceCode", ""),
                "errorMessage": error_message,
                "attempt": attempt + 1,
            }

    # All retries exhausted
    logger.error(
        f"All {max_retries} generation attempts failed for site {site_id}:\n"
        f"  Final status: {result.get('compilationStatus')}\n"
        f"  Final error: {result.get('error', 'Unknown')[:300]}"
    )
    return {
        "success": False,
        "compilationStatus": "retries_exhausted",
        "error": f"Failed after {max_retries} attempts: {result.get('error', 'Unknown')}",
        "finalAttemptResult": result,
    }
