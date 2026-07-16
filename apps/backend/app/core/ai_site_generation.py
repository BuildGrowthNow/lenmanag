"""
AI-native site generation - Phase 3 implementation.

Replaces deterministic section-by-section generation with a single AI pass
that produces complete landing page TSX code from the approved master brief.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.compiler_client import CompilerError, get_compiler_client
from app.core.llm import get_llm_client
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)

MAX_COMPILATION_RETRIES = 3


async def generate_landing_page_code(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    site_id: str,
    retry_context: dict[str, Any] | None = None,
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
        )

    # Generate code
    logger.info(f"Generating TSX code for site {site_id}")
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.8,  # Higher creativity for unique designs
        max_tokens=8192,  # Full page needs more tokens
    )

    # Extract code from response
    source_code = _extract_tsx_code(response)

    # Validate syntax
    validation_errors = _validate_tsx_source(source_code)
    if validation_errors:
        logger.warning(f"TSX validation errors: {validation_errors}")
        return {
            "success": False,
            "sourceCode": source_code,
            "compilationStatus": "validation_failed",
            "validationErrors": validation_errors,
            "error": f"Code validation failed: {', '.join(validation_errors[:3])}",
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
            return {
                "success": True,
                "sourceCode": source_code,
                "compiledBundleUrl": compile_result.get("bundleUrl"),
                "compilationStatus": "success",
                "bundleCode": compile_result.get("bundleCode"),
                "cssCode": compile_result.get("cssCode"),
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
) -> str:
    """Build the main generation prompt."""
    # Extract brand tokens
    brand_section = _build_brand_tokens_section(master_brief, extraction)

    # Extract content sections
    sections_list = "\n".join([
        f"  {i+1}. **{section.headline}** ({section.purpose})\n"
        f"     Approach: {section.suggestedApproach}\n"
        f"     Content: {section.contentSummary}\n"
        f"     Key points: {', '.join(section.contentPoints[:3])}"
        for i, section in enumerate(master_brief.sections)
    ])

    prompt = f"""You are an expert React developer building a landing page.

## Master Brief

**Business Goal**: {master_brief.businessGoal}
**Target Audience**: {master_brief.primaryAudience}
**Value Proposition**: {master_brief.valueProposition}
**Conversion Action**: {master_brief.conversionAction}
**Tone & Voice**: {master_brief.toneAndVoice}

**Visual Direction**:
- Style: {master_brief.visualStyle}
- Color Strategy: {master_brief.colorStrategy}
- Motion Level: {master_brief.motionLevel}
- Special Effects: {', '.join(master_brief.specialEffects) if master_brief.specialEffects else 'None'}

**Hero**:
- Headline: {master_brief.headline}
- Subheadline: {master_brief.subheadline}

**Page Sections**:
{sections_list}

**CTA Strategy**: {master_brief.ctaStrategy}

{brand_section}

## Available Libraries

Import and use these libraries as needed:
- React 19 with hooks (useState, useEffect, useRef)
- Tailwind CSS (utility-first styling, responsive breakpoints)
- framer-motion (motion.div, useScroll, useTransform, AnimatePresence, useInView)
- GSAP (gsap, ScrollTrigger for advanced animations)
- Three.js via @react-three/fiber and @react-three/drei (Canvas, useFrame, Box, Sphere, etc.)
- Lenis (smooth scrolling)
- shadcn/ui components (Button, Card, Badge, Separator, Dialog)
- Radix UI primitives (@radix-ui/react-*)
- Lucide React icons (import {{ IconName }} from 'lucide-react')
- embla-carousel-react (for carousels)

## Rules

1. Export a single default React component as the complete landing page
2. Use TypeScript/TSX syntax with proper types
3. All content must come from the brief - NO placeholder text or lorem ipsum
4. Self-contained component (all sections in one file, no external imports except libraries)
5. Use framer-motion for scroll animations and transitions
6. Be creative with layout - vary section widths, use asymmetry, create visual interest
7. Mobile responsive using Tailwind breakpoints (sm:, md:, lg:, xl:)
8. Keep code clean and performant
9. Images: use provided URLs from brand assets or leave image props empty
10. Aim for a premium, modern look (Awwwards-worthy)
11. Use the brand colors provided - don't invent new ones
12. Match the motion level specified: "{master_brief.motionLevel}"
13. Implement special effects if specified: {', '.join(master_brief.specialEffects) if master_brief.specialEffects else 'none'}

## Component Structure

```tsx
'use client';

import React, {{ useState, useEffect, useRef }} from 'react';
import {{ motion, useScroll, useTransform, AnimatePresence }} from 'framer-motion';
// ... other imports as needed

export default function LandingPage() {{
  // State and refs

  // Animation hooks

  return (
    <div className="min-h-screen bg-background text-foreground">
      {{/* Navigation */}}
      <nav className="...">...</nav>

      {{/* Hero Section */}}
      <section className="...">
        {master_brief.headline}
      </section>

      {{/* Additional sections based on brief */}}

      {{/* Footer with CTA */}}
    </div>
  );
}}
```

## Output

Return ONLY the complete TSX code. No markdown code fences, no explanations, just the raw TypeScript/React code.
Start with imports and end with the closing brace of the component.
"""

    return prompt


def _build_correction_prompt(
    *,
    master_brief: MasterBrief,  # noqa: ARG001
    extraction: ExtractionSnapshot,  # noqa: ARG001
    previous_code: str,
    error_message: str,
) -> str:
    """Build correction prompt for failed compilation."""
    prompt = f"""The landing page code you generated has compilation errors. Please fix them.

## Error Message
{error_message}

## Previous Code
```tsx
{previous_code}
```

## Instructions
1. Analyze the error message carefully
2. Fix the specific issues (syntax errors, import problems, type errors)
3. Keep the same design intent and content
4. Return ONLY the corrected TSX code, no markdown or explanations

## Common Issues to Check
- Missing imports
- Incorrect component syntax
- Type errors
- Invalid JSX structure
- Using unavailable libraries

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
        sections.append(f"**Primary Color**: {master_brief.brandAssets.primaryColor}")
    if master_brief.brandAssets.secondaryColor:
        sections.append(f"**Secondary Color**: {master_brief.brandAssets.secondaryColor}")

    # Logo
    if master_brief.brandAssets.logoUrl:
        sections.append(f"**Logo URL**: {master_brief.brandAssets.logoUrl}")

    # Typography
    if master_brief.brandAssets.fontFamily:
        sections.append(f"**Font Family**: {master_brief.brandAssets.fontFamily}")

    # Images
    if master_brief.brandAssets.imageUrls:
        image_list = "\n  ".join([f"- {url}" for url in master_brief.brandAssets.imageUrls[:5]])
        sections.append(f"**Available Images**:\n  {image_list}")

    if not sections:
        return "**Brand Assets**: Use default Tailwind colors and styling."

    return "## Brand Assets\n\n" + "\n".join(sections)


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


def _validate_tsx_source(source_code: str) -> list[str]:
    """
    Basic validation of TSX source code for safety and correctness.

    Returns list of validation errors, empty list if valid.
    """
    errors = []

    # Check for dangerous imports/patterns
    dangerous_patterns = [
        ("fs", "File system access not allowed"),
        ("child_process", "Process spawning not allowed"),
        ("eval(", "eval() not allowed"),
        ("Function(", "Function constructor not allowed"),
        ("__dirname", "Node.js paths not allowed"),
        ("process.env", "Environment access not allowed"),
    ]

    for pattern, message in dangerous_patterns:
        if pattern in source_code:
            errors.append(message)

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


async def generate_with_retry(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    site_id: str,
    max_retries: int = MAX_COMPILATION_RETRIES,
) -> dict[str, Any]:
    """
    Generate landing page code with automatic retry on compilation failure.

    Returns final result after retries.
    """
    retry_context = None
    result: dict[str, Any] = {
        "success": False,
        "compilationStatus": "not_attempted",
        "error": "No attempts made",
    }

    for attempt in range(max_retries):
        logger.info(f"Generation attempt {attempt + 1}/{max_retries} for site {site_id}")

        result = await generate_landing_page_code(
            master_brief=master_brief,
            extraction=extraction,
            site_id=site_id,
            retry_context=retry_context,
        )

        if result["success"]:
            logger.info(f"Successfully generated site {site_id} on attempt {attempt + 1}")
            return result

        # Prepare retry context
        retry_context = {
            "sourceCode": result["sourceCode"],
            "errorMessage": result.get("error", "Unknown error"),
            "attempt": attempt + 1,
        }

        logger.warning(
            f"Attempt {attempt + 1} failed for site {site_id}: {result.get('error')}"
        )

    # All retries exhausted
    logger.error(f"All {max_retries} generation attempts failed for site {site_id}")
    return {
        "success": False,
        "compilationStatus": "retries_exhausted",
        "error": f"Failed after {max_retries} attempts",
        "finalAttemptResult": result,
    }
