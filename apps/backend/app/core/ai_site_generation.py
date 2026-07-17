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
        max_tokens=32768,  # Large limit to ensure complete landing pages (never truncate)
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
    sections_list = "\n".join(
        [
            f"  {i + 1}. **{section.headline}** ({section.purpose})\n"
            f"     Approach: {section.suggestedApproach}\n"
            f"     Content: {section.contentSummary}\n"
            f"     Key points: {', '.join(section.contentPoints[:3])}"
            for i, section in enumerate(master_brief.sections)
        ]
    )

    prompt = f"""You are an expert React developer building a landing page.

## CRITICAL CONSTRAINTS — BROWSER-ONLY CODE

This is a React component that runs in the BROWSER, NOT Node.js.
Violating ANY of these rules will cause immediate rejection:

- DO NOT import or use ANY Node.js built-in modules: fs, path, child_process, os, crypto, buffer, stream, net, http, https, url, util, events, cluster, dgram, dns, readline, tls, zlib, vm, worker_threads, perf_hooks
- DO NOT use: __dirname, __filename, process.env, require(), module.exports
- DO NOT use: eval(), Function() constructor, new Function(), or any dynamic code execution
- DO NOT use filesystem operations of any kind (readFile, writeFile, readdir, etc.)
- DO NOT reference any server-side APIs or Node.js globals
- All data must come from props, React state, or hardcoded content from the brief
- Images must use URLs (https://...) or data URIs, NEVER filesystem paths like ./image.png or /public/image.png

## ALLOWED IMPORTS (use ONLY these)

- React and React hooks: import React, {{ useState, useEffect, useRef, useMemo, useCallback }} from 'react'
- Framer Motion: import {{ motion, useScroll, useTransform, AnimatePresence, useInView }} from 'framer-motion'
- GSAP: import gsap from 'gsap' and import {{ ScrollTrigger }} from 'gsap/ScrollTrigger'
- Three.js: import {{ Canvas, useFrame }} from '@react-three/fiber' and import {{ Box, Sphere, OrbitControls }} from '@react-three/drei'
- Lenis: import Lenis from 'lenis'
- shadcn/ui: import {{ Button, Card, Badge, Separator, Dialog }} from their respective paths
- Radix UI: import * from '@radix-ui/react-*'
- Lucide React icons: import {{ Phone, Mail, MapPin, CheckCircle, ArrowRight, Star, Menu, X }} from 'lucide-react'
- embla-carousel-react: import useEmblaCarousel from 'embla-carousel-react'

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
- Special Effects: {", ".join(master_brief.specialEffects) if master_brief.specialEffects else "None"}

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
4. Self-contained component (all sections in one file, no external imports except allowed libraries above)
5. Use framer-motion for scroll animations and transitions
6. Be creative with layout - vary section widths, use asymmetry, create visual interest
7. Mobile responsive using Tailwind breakpoints (sm:, md:, lg:, xl:)
8. Keep code clean and performant
9. Images: use provided URLs from brand assets or leave image props empty — NEVER use filesystem paths
10. Aim for a premium, modern look (Awwwards-worthy)
11. Use the brand colors provided - don't invent new ones
12. Match the motion level specified: "{master_brief.motionLevel}"
13. Implement special effects if specified: {", ".join(master_brief.specialEffects) if master_brief.specialEffects else "none"}
14. NEVER import fs, path, child_process, or any Node.js module

## Component Structure

```tsx
'use client';

import React, {{ useState, useEffect, useRef }} from 'react';
import {{ motion, useScroll, useTransform, AnimatePresence }} from 'framer-motion';
// ... other BROWSER-SAFE imports as needed (lucide-react, gsap, etc.)

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
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,  # noqa: ARG001
    previous_code: str,
    error_message: str,
) -> str:
    """Build correction prompt for failed compilation.

    Handles both syntax/validation errors and truncation issues.
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

GENERATE THE COMPLETE CODE NOW:
"""
    else:
        prompt = f"""The landing page code you generated has compilation errors. Please fix them.

## Error Message
{error_message}

## Previous Code
```tsx
{previous_code[:8000]}
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
- Node.js modules (fs, path, etc.) - NEVER use these
- Unclosed tags or components

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
        sections.append(
            f"**Secondary Color**: {master_brief.brandAssets.secondaryColor}"
        )

    # Logo
    if master_brief.brandAssets.logoUrl:
        sections.append(f"**Logo URL**: {master_brief.brandAssets.logoUrl}")

    # Typography
    if master_brief.brandAssets.fontFamily:
        sections.append(f"**Font Family**: {master_brief.brandAssets.fontFamily}")

    # Images
    if master_brief.brandAssets.imageUrls:
        image_list = "\n  ".join(
            [f"- {url}" for url in master_brief.brandAssets.imageUrls[:5]]
        )
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


async def _retry_generation_with_validation_feedback(
    *,
    llm: Any,
    original_code: str,
    validation_errors: list[str],
    master_brief: MasterBrief,  # noqa: ARG001
    extraction: ExtractionSnapshot,  # noqa: ARG001
    max_retries: int = 2,
) -> str:
    """
    Retry code generation with validation error feedback.

    Sends the LLM the original code with specific validation errors
    and asks it to fix the issues while keeping the same design.
    """
    errors_text = "\n".join(f"  - {error}" for error in validation_errors)

    for attempt in range(max_retries):
        logger.info(
            "Validation retry attempt %d/%d for code generation",
            attempt + 1,
            max_retries,
        )

        feedback_prompt = f"""Your previously generated React landing page component was REJECTED due to validation errors.

## VALIDATION ERRORS (must fix ALL of these):
{errors_text}

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
- framer-motion for animations
- GSAP and ScrollTrigger
- Three.js via @react-three/fiber and @react-three/drei
- Lenis for smooth scrolling
- shadcn/ui components
- Radix UI primitives
- Lucide React icons from 'lucide-react'
- embla-carousel-react

## PREVIOUS CODE (with errors):
```tsx
{original_code[:6000]}
```

## INSTRUCTIONS:
1. Fix ALL validation errors listed above
2. Keep the same design intent, layout, and content
3. Remove any Node.js imports (fs, path, etc.) and replace with browser-safe alternatives
4. Return ONLY the corrected TSX code — no markdown fences, no explanations
"""

        response = await llm.generate_text(
            prompt=feedback_prompt,
            temperature=0.5,
            max_tokens=32768,  # Match increased limit for complete code
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


async def generate_with_retry(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    site_id: str,
    max_retries: int = MAX_COMPILATION_RETRIES,
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
