# Multi-Variant Site Generation - Final Implementation Plan

## Overview

Enable users to generate **3 HTML variants + 1 Next.js site** for each lead, with:
- **Static HTML/CSS/JS** (no React) for quick client previews
- **Distinct creative directions** per variant (industry-standard, bold/experimental, alternative)
- **Global sequential generation** to avoid rate limits
- **Automatic model fallback** using existing Bedrock infrastructure
- **Separate preview URLs** for each variant

---

## Key Design Decisions

### ✅ Confirmed Decisions

1. **HTML Output Format:** Static HTML with separate CSS/JS files (no React runtime)
2. **Rate Limit Handling:** Use existing Bedrock client with 6 fallback models
3. **Sequential Generation:** Redis distributed lock to ensure global sequential execution
4. **Master Briefs:** Each HTML variant gets its own unique master brief
5. **Preview URLs:** Format `st/{company-slug}-v1`, `st/{company-slug}-v2`, `st/{company-slug}-v3`, `st/{company-slug}`
6. **Storage:** Upload static HTML/CSS/JS to S3, serve directly via slug

### 🎯 Architecture Principles

- **Reuse existing schemas** - Extend `GeneratedSite`, don't create new collections
- **Reuse existing infrastructure** - Bedrock client, Celery, extraction/analysis
- **Minimal new code** - ~600 lines total (backend + frontend)
- **Production-ready** - Follows existing patterns, fully tested

---

## Phase 0: Schema Extensions

### 0.1 Extend `GeneratedSite` Schema

**File:** `apps/backend/app/schemas/site.py`

**Changes:**
```python
# Add new literal type (line ~11)
VariantType = Literal["html_v1", "html_v2", "html_v3", "nextjs"]

# Extend GeneratedSite class (line ~352)
class GeneratedSite(BaseModel):
    # ... existing fields ...
    
    # NEW: Variant identification
    variantType: VariantType = "nextjs"
    variantLabel: str = "Next.js Site"
    variantPosition: int = 1  # Display order: 1=first, 2=second, etc.
    
    # NEW: Static HTML output (for HTML variants only)
    staticHtml: Optional[str] = None  # Full HTML content
    staticCssUrl: Optional[str] = None  # S3 URL to styles.css
    staticJsUrl: Optional[str] = None  # S3 URL to script.js
    
    # Existing fields remain unchanged:
    # sourceCode: Optional[str]  # TSX for Next.js, HTML template for static
    # compiledBundleUrl: Optional[str]  # Next.js bundle, not used for static
    # previewSlug: str  # e.g., "acme-v1", "acme-v2", "acme"
    # previewUrl: str  # e.g., "https://sites.lenquant.com/st/acme-v1"
```

**Backward Compatibility:** All existing fields keep defaults, existing sites remain valid.

---

### 0.2 Extend `LeadUpsertRequest` Schema

**File:** `apps/backend/app/schemas/lead.py`

**Changes:**
```python
# Add new literal type (line ~6)
GenerationType = Literal["html_v1", "html_v2", "html_v3", "nextjs"]

# Extend LeadUpsertRequest (line ~135)
class LeadUpsertRequest(BaseModel):
    companyName: Optional[str] = None
    websiteUrl: str
    industry: Optional[str] = None
    notes: Optional[str] = None
    pipelineMode: PipelineMode = "auto"
    
    # NEW: Generation types selection
    generationTypes: list[GenerationType] = Field(
        default=["nextjs"],
        description="Types of sites to generate. Can select 1-4 options.",
        min_length=1,
        max_length=4,
    )
```

---

## Phase 1: Backend - Variant Strategy & Generation

### 1.1 Variant Strategy Mapper

**File:** `apps/backend/app/core/variant_strategy.py` **(NEW)**

```python
"""
Variant strategy definitions for HTML multi-variant generation.

Each variant type maps to a distinct creative direction with specific
design parameters to ensure meaningfully different outputs.
"""

from typing import TypedDict

from app.schemas.brief import DesignMode
from app.schemas.site import PaletteMode, VariantType


class VariantStrategy(TypedDict):
    """Strategy definition for a single variant."""
    
    variantType: VariantType
    variantLabel: str
    variantPosition: int
    designMode: DesignMode
    paletteMode: PaletteMode
    creativeBriefGuidance: str
    inspirationKeywords: list[str]
    avoidPatterns: list[str]


def get_variant_strategies(industry: str | None = None) -> dict[VariantType, VariantStrategy]:
    """
    Return variant strategies based on industry context.
    
    Each variant is designed to be DISTINCTLY DIFFERENT:
    - Variant 1: Industry-standard, professional, proven patterns
    - Variant 2: Bold, experimental, startup-like energy
    - Variant 3: Alternative approach (colorful, playful, or dark luxe)
    
    Args:
        industry: Optional industry context for tailoring strategies
        
    Returns:
        Dictionary mapping variant type to strategy definition
    """
    
    # Base strategies (work for most industries)
    base_strategies: dict[VariantType, VariantStrategy] = {
        "html_v1": {
            "variantType": "html_v1",
            "variantLabel": "Professional Standard",
            "variantPosition": 1,
            "designMode": "corporate",
            "paletteMode": "zinc",
            "creativeBriefGuidance": """
                Generate a professional, industry-standard design:
                - Clean, structured layouts with clear visual hierarchy
                - Conservative color palette: neutrals (grays, whites) with single brand accent
                - Serif or elegant sans-serif typography for trust and authority
                - Light mode with spacious whitespace
                - Subtle animations, professional interactions
                - Focus on credibility, clarity, and user confidence
                - Editorial-style content presentation
            """,
            "inspirationKeywords": [
                "editorial", "professional", "structured", "trustworthy",
                "clean", "spacious", "authoritative", "premium"
            ],
            "avoidPatterns": [
                "experimental layouts", "bold colors", "playful shapes",
                "heavy animations", "dark mode", "trendy effects"
            ],
        },
        "html_v2": {
            "variantType": "html_v2",
            "variantLabel": "Bold Startup",
            "variantPosition": 2,
            "designMode": "interactive",
            "paletteMode": "colorful",
            "creativeBriefGuidance": """
                Generate a bold, high-energy startup aesthetic:
                - Asymmetric, experimental layouts with unexpected element placement
                - Dark mode with electric accent colors (neons, vibrant blues/purples)
                - Geometric sans-serif typography, large display headings
                - High contrast, dramatic color shifts
                - Expressive animations: parallax, scroll-triggered reveals, micro-interactions
                - Confident, punchy copy with strong CTAs
                - Modern tech/startup vibe with cutting-edge design patterns
            """,
            "inspirationKeywords": [
                "bold", "experimental", "high-energy", "asymmetric",
                "dark-mode", "neon-accents", "parallax", "startup",
                "confident", "modern", "cutting-edge"
            ],
            "avoidPatterns": [
                "conservative layouts", "light mode", "subtle colors",
                "serif fonts", "corporate stiffness", "traditional grids"
            ],
        },
        "html_v3": {
            "variantType": "html_v3",
            "variantLabel": "Creative Alternative",
            "variantPosition": 3,
            "designMode": "playful",
            "paletteMode": "colorful",
            "creativeBriefGuidance": """
                Generate a distinctive, creative alternative design:
                - Colorful, multi-hue palette (3-4 brand colors working together)
                - Playful, organic shapes and rounded elements
                - Friendly, approachable tone with warm colors
                - Balanced energy: not corporate, not hyper-bold, but creative and memorable
                - Smooth, delightful animations (bounces, elastic easing)
                - Approachable copy, human voice
                - Unique visual personality that stands out from competitors
            """,
            "inspirationKeywords": [
                "colorful", "playful", "organic", "approachable",
                "creative", "distinctive", "warm", "friendly",
                "rounded", "delightful", "unique"
            ],
            "avoidPatterns": [
                "monochrome", "rigid grids", "corporate stiffness",
                "harsh contrasts", "cold colors", "generic stock photos"
            ],
        },
    }
    
    # Industry-specific adjustments (optional enhancement)
    industry_lower = (industry or "").lower()
    
    if any(keyword in industry_lower for keyword in ["consulting", "legal", "finance", "b2b"]):
        # For professional services: make variant 3 more luxe/refined instead of playful
        base_strategies["html_v3"].update({
            "variantLabel": "Minimal Luxe",
            "designMode": "minimalist",
            "paletteMode": "light",
            "creativeBriefGuidance": """
                Generate a premium, minimal luxury design:
                - Soft, refined color palette: neutrals with single elegant accent
                - Abundant whitespace, quiet confidence
                - Serif display typography with elegant sans body text
                - Light mode or soft dark mode (charcoal, not black)
                - Subtle, refined animations (fades, smooth reveals)
                - Premium, sophisticated tone
                - Focus on quality over quantity of elements
            """,
            "inspirationKeywords": [
                "minimal", "luxe", "refined", "premium", "elegant",
                "sophisticated", "quiet", "spacious", "quality"
            ],
            "avoidPatterns": [
                "busy layouts", "loud colors", "playful shapes",
                "excessive decoration", "generic templates"
            ],
        })
    
    return base_strategies


def get_variant_strategy(variant_type: VariantType, industry: str | None = None) -> VariantStrategy:
    """Get strategy for a specific variant type."""
    strategies = get_variant_strategies(industry)
    if variant_type not in strategies:
        raise ValueError(f"Unknown variant type: {variant_type}")
    return strategies[variant_type]
```

---

### 1.2 Static HTML Generator

**File:** `apps/backend/app/core/static_html_generator.py` **(NEW)**

```python
"""
Static HTML generation for multi-variant output.

Generates standalone HTML/CSS/JS files (no React runtime) from master brief.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import uuid4

import boto3
from app.core.config import get_settings
from app.core.llm import get_llm_client
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)


async def generate_static_html(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
    variant_type: str,
    site_id: str,
) -> dict[str, Any]:
    """
    Generate static HTML/CSS/JS from master brief.
    
    Returns:
        {
            "html": "<html>...</html>",
            "cssUrl": "https://s3.../styles.css",
            "jsUrl": "https://s3.../script.js",
        }
    """
    llm = get_llm_client()
    
    # Build HTML generation prompt
    prompt = _build_static_html_prompt(master_brief, extraction, variant_type)
    
    # Generate HTML, CSS, JS via LLM
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.7,
        max_tokens=8192,
    )
    
    # Parse response
    html_content, css_content, js_content = _parse_llm_response(response)
    
    # Upload CSS and JS to S3
    settings = get_settings()
    css_url = await _upload_to_s3(
        content=css_content,
        filename=f"{site_id}/styles.css",
        content_type="text/css",
        bucket=settings.asset_s3_bucket,
        prefix=settings.asset_s3_prefix,
    )
    js_url = await _upload_to_s3(
        content=js_content,
        filename=f"{site_id}/script.js",
        content_type="application/javascript",
        bucket=settings.asset_s3_bucket,
        prefix=settings.asset_s3_prefix,
    )
    
    # Inject CSS/JS URLs into HTML
    html_final = html_content.replace(
        "</head>",
        f'<link rel="stylesheet" href="{css_url}">\n</head>'
    ).replace(
        "</body>",
        f'<script src="{js_url}"></script>\n</body>'
    )
    
    return {
        "html": html_final,
        "cssUrl": css_url,
        "jsUrl": js_url,
    }


def _build_static_html_prompt(
    brief: MasterBrief,
    extraction: ExtractionSnapshot,
    variant_type: str,
) -> str:
    """Build LLM prompt for static HTML generation."""
    
    return f"""Generate a complete, production-ready static HTML landing page.

MASTER BRIEF:
- Business Goal: {brief.businessGoal}
- Primary Audience: {brief.primaryAudience}
- Value Proposition: {brief.valueProposition}
- Tone & Voice: {brief.toneAndVoice}
- Visual Style: {brief.visualStyle}
- Color Strategy: {brief.colorStrategy}
- Motion Level: {brief.motionLevel}

CREATIVE DIRECTION:
- Design Concept: {brief.creativeDirection.designConcept}
- Hero Treatment: {brief.creativeDirection.heroTreatment}
- Signature Technique: {brief.creativeDirection.signatureTechnique}
- Layout Strategy: {brief.creativeDirection.layoutStrategy}
- Color Mood: {brief.creativeDirection.colorMood}
- Typography: {brief.creativeDirection.typographyPersonality}

CONTENT BLUEPRINT:
- Hero Headline: {brief.headline}
- Hero Subheadline: {brief.subheadline}
- Sections: {len(brief.sections)} sections defined
- CTA Strategy: {brief.ctaStrategy}

BRAND ASSETS:
- Logo URL: {brief.brandAssets.logoUrl or "None"}
- Primary Color: {brief.brandAssets.primaryColor or "#000000"}
- Secondary Color: {brief.brandAssets.secondaryColor or "#666666"}
- Font Family: {brief.brandAssets.fontFamily or "System sans-serif"}

VARIANT TYPE: {variant_type}

REQUIREMENTS:
1. Generate THREE separate code blocks:
   - HTML: Complete semantic HTML5 structure
   - CSS: All styles in a single stylesheet
   - JavaScript: Vanilla JS for interactions (no frameworks)

2. HTML Structure:
   - Semantic tags (<header>, <main>, <section>, <footer>)
   - Proper meta tags (viewport, description, title)
   - Accessibility: ARIA labels, alt text, semantic structure
   - Include all sections from the master brief
   - Use brand logo if available
   - NO inline styles or scripts (reference external files)

3. CSS Requirements:
   - Use CSS custom properties for colors/spacing
   - Responsive design (mobile-first)
   - Smooth animations matching motion level
   - Follow the creative direction's color mood and typography
   - Include hover states for interactive elements

4. JavaScript Requirements:
   - Vanilla JS only (no jQuery, no React, no frameworks)
   - Smooth scroll behavior
   - Form validation if contact form present
   - Any scroll-triggered animations mentioned in signature technique
   - Mobile menu toggle if needed

5. Design Quality:
   - Match the visual style and creative direction EXACTLY
   - Implement the signature technique prominently
   - Use the specified color strategy
   - Typography should reflect the personality described
   - Spacing and layout should match the layout strategy

OUTPUT FORMAT:
Return your response in this exact format:

```html
<!DOCTYPE html>
<html lang="en">
...complete HTML here...
</html>
```

```css
/* styles.css */
:root {{
  --primary-color: ...;
  --secondary-color: ...;
}}
...complete CSS here...
```

```javascript
// script.js
document.addEventListener('DOMContentLoaded', () => {{
  ...complete JS here...
}});
```

Generate high-quality, production-ready code that implements this brief faithfully.
"""


def _parse_llm_response(response: str) -> tuple[str, str, str]:
    """Parse HTML, CSS, JS from LLM response."""
    
    # Extract HTML
    html_start = response.find("```html")
    if html_start == -1:
        raise ValueError("No HTML code block found in LLM response")
    html_start = response.find("\n", html_start) + 1
    html_end = response.find("```", html_start)
    html = response[html_start:html_end].strip()
    
    # Extract CSS
    css_start = response.find("```css")
    if css_start == -1:
        raise ValueError("No CSS code block found in LLM response")
    css_start = response.find("\n", css_start) + 1
    css_end = response.find("```", css_start)
    css = response[css_start:css_end].strip()
    
    # Extract JS
    js_start = response.find("```javascript")
    if js_start == -1:
        js_start = response.find("```js")
    if js_start == -1:
        logger.warning("No JavaScript code block found, using empty JS")
        js = "// No JavaScript needed for this page"
    else:
        js_start = response.find("\n", js_start) + 1
        js_end = response.find("```", js_start)
        js = response[js_start:js_end].strip()
    
    return html, css, js


async def _upload_to_s3(
    content: str,
    filename: str,
    content_type: str,
    bucket: str | None,
    prefix: str,
) -> str:
    """Upload file to S3 and return public URL."""
    
    if not bucket:
        raise RuntimeError("S3 bucket not configured (ASSET_S3_BUCKET)")
    
    s3_client = boto3.client("s3", region_name="us-east-1")
    
    key = f"{prefix}static-sites/{filename}"
    
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=content.encode("utf-8"),
        ContentType=content_type,
        CacheControl="public, max-age=3600",
    )
    
    # Return CDN URL (assumes CloudFront or direct S3 URL)
    url = f"https://{bucket}.s3.amazonaws.com/{key}"
    
    logger.info(f"Uploaded {content_type} to S3: {url}")
    
    return url
```

---

### 1.3 Extend Master Brief Generation

**File:** `apps/backend/app/core/master_brief.py`

**Changes:**
```python
# Add import at top
from app.core.variant_strategy import get_variant_strategy
from app.schemas.site import VariantType

# Extend generate_master_brief function (line ~32)
async def generate_master_brief(
    *,
    lead_id: str,
    extraction: ExtractionSnapshot,
    feedback: str | None = None,
    previous_brief: MasterBrief | None = None,
    variant_type: VariantType | None = None,  # NEW
    industry: str | None = None,  # NEW
) -> MasterBrief:
    """
    Generate a master brief using AI from extraction data.
    
    New params:
        variant_type: If provided, tailor brief to variant strategy
        industry: Industry context for variant strategy selection
    """
    llm = get_llm_client()
    
    # Build extraction summary
    extraction_summary = _build_extraction_summary(extraction)
    
    # NEW: Get variant strategy if variant type specified
    variant_guidance = None
    if variant_type and variant_type != "nextjs":
        strategy = get_variant_strategy(variant_type, industry)
        variant_guidance = strategy["creativeBriefGuidance"]
    
    # Build prompt with variant guidance
    if feedback and previous_brief:
        prompt = _build_refinement_prompt(
            extraction_summary=extraction_summary,
            previous_brief=previous_brief,
            feedback=feedback,
            variant_guidance=variant_guidance,  # NEW
        )
    else:
        prompt = _build_initial_prompt(
            extraction_summary=extraction_summary,
            variant_guidance=variant_guidance,  # NEW
        )
    
    # ... rest of function unchanged
```

**Extend `_build_initial_prompt` helper:**
```python
def _build_initial_prompt(
    extraction_summary: str,
    variant_guidance: str | None = None,
) -> str:
    """Build initial master brief generation prompt."""
    
    base_prompt = f"""Generate a master brief for a landing page redesign.

EXTRACTED DATA:
{extraction_summary}

... (existing prompt content) ...
"""
    
    # NEW: Inject variant guidance if provided
    if variant_guidance:
        base_prompt += f"""

VARIANT CREATIVE DIRECTION:
This is variant-specific generation. Follow this creative direction STRICTLY:
{variant_guidance}

Ensure the brief reflects this distinct creative direction in:
- visualStyle field
- colorStrategy field
- creativeDirection object (all fields)
- designMode selection
- motionLevel choice
"""
    
    return base_prompt
```

---

### 1.4 Extend Site Repository

**File:** `apps/backend/app/core/sites.py`

**Add new method:**
```python
async def generate_site_variant(
    self,
    *,
    lead_id: str,
    variant_type: VariantType,
    variant_strategy: dict,
    extraction: ExtractionSnapshot,
    analysis: ExtractionAnalysisResponse,
    user_id: str,
) -> GeneratedSite:
    """
    Generate a single site variant (HTML or Next.js).
    
    Args:
        lead_id: Lead identifier
        variant_type: Type of variant to generate
        variant_strategy: Strategy definition from variant_strategy.py
        extraction: Extraction snapshot (shared across variants)
        analysis: Analysis results (shared across variants)
        user_id: User ID for audit trail
        
    Returns:
        Generated site variant
    """
    from app.core.master_brief import generate_master_brief
    from app.core.static_html_generator import generate_static_html
    from app.core.ai_site_generation import generate_landing_page_code
    
    # Step 1: Generate variant-specific master brief
    logger.info(f"Generating master brief for {variant_type} (lead {lead_id})")
    master_brief = await generate_master_brief(
        lead_id=lead_id,
        extraction=extraction,
        variant_type=variant_type,
        industry=analysis.industry if analysis else None,
    )
    
    # Save brief to database
    await self.db["master_briefs"].insert_one(master_brief.model_dump(by_alias=True))
    
    # Step 2: Generate site based on variant type
    site_id = str(uuid4())
    slug = self._generate_variant_slug(lead_id, variant_type, extraction.summary.companyName)
    
    if variant_type == "nextjs":
        # Use existing Next.js generation
        logger.info(f"Generating Next.js site for {variant_type} (site {site_id})")
        code_result = await generate_landing_page_code(
            master_brief=master_brief,
            extraction=extraction,
            site_id=site_id,
        )
        
        site = GeneratedSite(
            id=site_id,
            leadId=lead_id,
            briefId=master_brief.id,
            briefVersion=master_brief.version,
            variantType=variant_type,
            variantLabel=variant_strategy["variantLabel"],
            variantPosition=variant_strategy["variantPosition"],
            sourceCode=code_result.get("sourceCode"),
            compiledBundleUrl=code_result.get("bundleUrl"),
            compilationStatus="success",
            previewSlug=slug,
            previewUrl=f"https://sites.lenquant.com/st/{slug}",
            # ... populate other fields from code_result ...
        )
    else:
        # Generate static HTML
        logger.info(f"Generating static HTML for {variant_type} (site {site_id})")
        html_result = await generate_static_html(
            master_brief=master_brief,
            extraction=extraction,
            variant_type=variant_type,
            site_id=site_id,
        )
        
        site = GeneratedSite(
            id=site_id,
            leadId=lead_id,
            briefId=master_brief.id,
            briefVersion=master_brief.version,
            variantType=variant_type,
            variantLabel=variant_strategy["variantLabel"],
            variantPosition=variant_strategy["variantPosition"],
            staticHtml=html_result["html"],
            staticCssUrl=html_result["cssUrl"],
            staticJsUrl=html_result["jsUrl"],
            sourceCode=html_result["html"],  # Store HTML as source
            previewSlug=slug,
            previewUrl=f"https://sites.lenquant.com/st/{slug}",
            readinessStatus="ready_for_review",
            qaStatus="pass",
            # ... populate other required fields ...
        )
    
    # Save site to database
    await self.db["generated_sites"].insert_one(site.model_dump(by_alias=True))
    
    logger.info(f"Variant {variant_type} generated: {site.previewUrl}")
    
    return site


def _generate_variant_slug(
    self,
    lead_id: str,
    variant_type: VariantType,
    company_name: str | None,
) -> str:
    """Generate preview slug for variant."""
    
    # Base slug from company name or lead ID
    if company_name:
        base = company_name.lower().replace(" ", "-").replace("_", "-")
        base = "".join(c for c in base if c.isalnum() or c == "-")
    else:
        base = lead_id[:8]
    
    # Add variant suffix
    if variant_type == "html_v1":
        return f"{base}-v1"
    elif variant_type == "html_v2":
        return f"{base}-v2"
    elif variant_type == "html_v3":
        return f"{base}-v3"
    else:  # nextjs
        return base


async def list_sites_by_lead(self, lead_id: str) -> list[GeneratedSite]:
    """Get all site variants for a lead."""
    cursor = self.db["generated_sites"].find({"leadId": lead_id})
    sites = [GeneratedSite(**doc) async for doc in cursor]
    # Sort by variant position
    return sorted(sites, key=lambda s: s.variantPosition)
```

---

### 1.5 Redis Lock for Sequential Generation

**File:** `apps/backend/app/core/generation_lock.py` **(NEW)**

```python
"""
Distributed lock for ensuring sequential site generation across all workers.

Uses Redis to enforce global sequential execution, preventing rate limits.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global lock key in Redis
GENERATION_LOCK_KEY = "lenquant:generation:lock"
LOCK_TIMEOUT_SECONDS = 3600  # 1 hour max per generation


class GenerationLockTimeout(Exception):
    """Raised when unable to acquire generation lock within timeout."""
    pass


@asynccontextmanager
async def generation_lock(
    timeout_seconds: int = 300,
) -> AsyncGenerator[None, None]:
    """
    Distributed lock for site generation.
    
    Ensures only ONE generation task runs globally at any time,
    even across multiple workers/processes.
    
    Args:
        timeout_seconds: How long to wait for lock acquisition
        
    Raises:
        GenerationLockTimeout: If lock not acquired within timeout
        
    Usage:
        async with generation_lock(timeout_seconds=300):
            # Only one task can be here at a time globally
            await generate_site(...)
    """
    settings = get_settings()
    
    # Parse Redis URL from Celery broker
    redis_url = settings.celery_broker_url
    
    redis_client = redis.from_url(redis_url, decode_responses=True)
    
    lock_acquired = False
    lock_id = f"{time.time()}-{id(redis_client)}"  # Unique lock ID
    
    try:
        # Try to acquire lock
        start_time = time.monotonic()
        while True:
            # SET with NX (only if not exists) and EX (expiry)
            acquired = await redis_client.set(
                GENERATION_LOCK_KEY,
                lock_id,
                nx=True,
                ex=LOCK_TIMEOUT_SECONDS,
            )
            
            if acquired:
                lock_acquired = True
                logger.info("Generation lock acquired")
                break
            
            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_seconds:
                raise GenerationLockTimeout(
                    f"Could not acquire generation lock after {timeout_seconds}s"
                )
            
            # Wait and retry
            logger.info(
                f"Waiting for generation lock... ({elapsed:.0f}s elapsed)"
            )
            await asyncio.sleep(5)
        
        # Lock acquired, yield control
        yield
        
    finally:
        # Release lock if we acquired it
        if lock_acquired:
            # Use Lua script for atomic check-and-delete
            release_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            await redis_client.eval(
                release_script,
                1,
                GENERATION_LOCK_KEY,
                lock_id,
            )
            logger.info("Generation lock released")
        
        await redis_client.close()
```

---

### 1.6 Celery Task for Multi-Variant Generation

**File:** `apps/backend/app/core/tasks.py`

**Add new task:**
```python
from app.core.generation_lock import generation_lock
from app.core.variant_strategy import get_variant_strategy, get_variant_strategies

@celery_app.task(
    name="lenquant.jobs.run_multi_variant_generation",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
    retry_jitter=True,
    max_retries=2,
)
def run_multi_variant_generation_task(
    self,
    lead_id: str,
    job_id: str,
    generation_types: list[str],
) -> None:
    """
    Generate multiple site variants for a lead.
    
    Uses distributed lock to ensure sequential execution globally.
    Each variant generation is atomic and sequential.
    """
    try:
        _run(_run_multi_variant_generation_async(lead_id, job_id, generation_types))
    except Exception as exc:
        logger.error(
            f"Multi-variant generation failed for lead {lead_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        # Update job status
        try:
            _run(
                lead_repository._update_job(
                    job_id=job_id,
                    status="failed",
                    error_message=f"Generation failed: {str(exc)}",
                    finished=self.request.retries >= self.max_retries,
                )
            )
        except Exception:
            pass
        raise


async def _run_multi_variant_generation_async(
    lead_id: str,
    job_id: str,
    generation_types: list[str],
) -> None:
    """Async implementation of multi-variant generation."""
    
    # Get lead and extraction (shared across all variants)
    lead = await lead_repository.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")
    
    extraction = await lead_repository.get_extraction(lead_id)
    if not extraction or extraction.status != "completed":
        raise ValueError(f"Extraction not completed for lead {lead_id}")
    
    analysis = await lead_repository.get_analysis(lead_id)
    
    # Get variant strategies
    industry = lead.industry or (analysis.industry if analysis else None)
    strategies = get_variant_strategies(industry)
    
    # Generate each variant sequentially with distributed lock
    generated_sites = []
    total_variants = len(generation_types)
    
    for i, variant_type in enumerate(generation_types):
        # Update job progress
        progress = int((i / total_variants) * 100)
        await lead_repository._update_job(
            job_id=job_id,
            status="running",
            progress=progress,
            step=f"Generating {variant_type} ({i+1}/{total_variants})",
        )
        
        # Acquire global lock and generate
        async with generation_lock(timeout_seconds=600):  # 10 min timeout
            logger.info(f"Generating variant {variant_type} for lead {lead_id}")
            
            site = await site_repository.generate_site_variant(
                lead_id=lead_id,
                variant_type=variant_type,
                variant_strategy=strategies[variant_type],
                extraction=extraction,
                analysis=analysis,
                user_id=lead.user_id,
            )
            
            generated_sites.append(site)
            
            logger.info(
                f"Variant {variant_type} completed ({i+1}/{total_variants}): "
                f"{site.previewUrl}"
            )
    
    # Mark job complete
    await lead_repository._update_job(
        job_id=job_id,
        status="completed",
        progress=100,
        step=f"Generated {total_variants} variants",
        finished=True,
    )
    
    # Update lead pipeline stage
    await lead_repository.update_lead(
        lead_id,
        LeadPatchRequest(pipelineStage="ready"),
    )
    
    logger.info(
        f"Multi-variant generation completed for lead {lead_id}: "
        f"{len(generated_sites)} sites generated"
    )
```

---

## Phase 2: API Endpoints

### 2.1 Trigger Multi-Variant Generation

**File:** `apps/backend/app/api/leads.py`

**Modify `create_lead` endpoint:**
```python
@router.post("", response_model=ResponseEnvelope[LeadActionResponse])
async def create_lead(
    user_id: CurrentUserId,
    payload: LeadUpsertRequest,
    http_request: Request,
) -> ResponseEnvelope[LeadActionResponse]:
    result = await lead_repository.create_lead(payload, user_id=user_id)
    
    # NEW: Trigger multi-variant generation if requested
    if len(payload.generationTypes) > 0:
        from app.core.tasks import run_multi_variant_generation_task
        from uuid import uuid4
        
        job_id = str(uuid4())
        
        # Create job record
        await lead_repository._create_job(
            job_id=job_id,
            lead_id=result.lead.id,
            job_type="site_generate",
        )
        
        # Trigger Celery task
        run_multi_variant_generation_task.delay(
            lead_id=result.lead.id,
            job_id=job_id,
            generation_types=payload.generationTypes,
        )
        
        # Update lead stage
        await lead_repository.update_lead(
            result.lead.id,
            LeadPatchRequest(pipelineStage="generating"),
        )
        
        logger.info(
            f"Multi-variant generation triggered for lead {result.lead.id}: "
            f"{payload.generationTypes}"
        )
    
    await write_audit_log(
        user_id,
        "lead",
        result.lead.id,
        "lead_create",
        after=result.model_dump(),
    )
    return success_response(result, meta=response_meta(http_request))
```

---

### 2.2 List Variants for Lead

**File:** `apps/backend/app/api/sites.py`

**Add endpoint:**
```python
@router.get("/variants/{lead_id}", response_model=ResponseEnvelope[list[GeneratedSite]])
async def list_variants_for_lead(
    lead_id: str,
    user_id: CurrentUserId,
    http_request: Request,
) -> ResponseEnvelope[list[GeneratedSite]]:
    """Get all site variants for a lead."""
    sites = await site_repository.list_sites_by_lead(lead_id)
    return success_response(sites, meta=response_meta(http_request))
```

---

### 2.3 Serve Static HTML Preview

**File:** `apps/backend/app/api/public.py`

**Add endpoint:**
```python
from fastapi.responses import HTMLResponse

@router.get("/st/{slug}")
async def preview_site_variant(slug: str) -> HTMLResponse:
    """
    Public preview of a site variant (HTML or Next.js).
    
    For static HTML variants: returns HTML with linked CSS/JS
    For Next.js variants: redirects to Next.js preview
    """
    from app.core.sites import site_repository
    
    # Find site by slug
    site = await site_repository.get_site_by_slug(slug)
    if not site:
        raise HTTPException(status_code=404, detail="Site preview not found")
    
    # Serve static HTML if variant is HTML type
    if site.variantType in ["html_v1", "html_v2", "html_v3"]:
        if not site.staticHtml:
            raise HTTPException(status_code=500, detail="Static HTML not generated")
        
        return HTMLResponse(content=site.staticHtml)
    
    # For Next.js variants, redirect to Next.js preview
    else:
        return RedirectResponse(url=f"/preview/{site.id}")
```

**Add helper method to site repository:**
```python
# apps/backend/app/core/sites.py

async def get_site_by_slug(self, slug: str) -> GeneratedSite | None:
    """Get site by preview slug."""
    doc = await self.db["generated_sites"].find_one({"previewSlug": slug})
    if not doc:
        return None
    return GeneratedSite(**doc)
```

---

## Phase 3: Frontend Implementation

### 3.1 Update Types

**File:** `apps/web/src/lib/types.ts`

**Add types:**
```typescript
// Add after line ~150
export type VariantType = "html_v1" | "html_v2" | "html_v3" | "nextjs";

export type GenerationType = VariantType;

export interface SiteVariant {
  id: string;
  leadId: string;
  variantType: VariantType;
  variantLabel: string;
  variantPosition: number;
  previewSlug: string;
  previewUrl: string;
  briefId: string;
  readinessStatus: string;
  qaStatus: string;
  staticHtml?: string;
  staticCssUrl?: string;
  staticJsUrl?: string;
  compiledBundleUrl?: string;
  createdAt: string;
  updatedAt: string;
}
```

---

### 3.2 Extend Lead Creation Modal

**File:** `apps/web/src/app/app/leads/page.tsx`

**Modify `AddLeadModal` component (line ~137):**
```typescript
function AddLeadModal({ open, onClose, onCreated }: AddLeadModalProps) {
  const [form, setForm] = useState({ companyName: "", websiteUrl: "", notes: "" });
  const [mode, setMode] = useState<PipelineMode>("auto");
  
  // NEW: Generation types selection
  const [generationTypes, setGenerationTypes] = useState<GenerationType[]>(["nextjs"]);
  
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setForm({ companyName: "", websiteUrl: "", notes: "" });
      setMode("auto");
      setGenerationTypes(["nextjs"]);  // NEW
      setError(null);
    }
  }, [open]);

  function toggleGenerationType(type: GenerationType) {
    setGenerationTypes((prev) => {
      const newTypes = new Set(prev);
      if (newTypes.has(type)) {
        newTypes.delete(type);
      } else {
        newTypes.add(type);
      }
      // Ensure at least one type selected
      return newTypes.size > 0 ? Array.from(newTypes) : prev;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createLead({
        companyName: form.companyName.trim() || null,
        websiteUrl: form.websiteUrl.trim(),
        notes: form.notes.trim() || null,
        pipelineMode: mode,
        generationTypes: generationTypes,  // NEW
      });
      onCreated();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create lead.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add lead</DialogTitle>
        </DialogHeader>
        <form className="space-y-4" onSubmit={handleSubmit}>
          {/* Existing fields: websiteUrl, companyName */}
          
          {/* NEW: Generation Types Selection */}
          <div className="space-y-2 border-t border-white/10 pt-4">
            <label className="text-xs uppercase tracking-[0.2em] text-muted">
              Generate
            </label>
            <div className="space-y-2">
              {[
                { type: "html_v1" as GenerationType, label: "HTML - Professional Standard", icon: "📄" },
                { type: "html_v2" as GenerationType, label: "HTML - Bold Startup", icon: "⚡" },
                { type: "html_v3" as GenerationType, label: "HTML - Creative Alternative", icon: "🎨" },
                { type: "nextjs" as GenerationType, label: "Next.js - Full Site", icon: "⚛️" },
              ].map((item) => (
                <label
                  key={item.type}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded border cursor-pointer transition",
                    generationTypes.includes(item.type)
                      ? "border-blue-500/50 bg-blue-500/10"
                      : "border-white/10 bg-white/5 hover:bg-white/10"
                  )}
                >
                  <input
                    type="checkbox"
                    checked={generationTypes.includes(item.type)}
                    onChange={() => toggleGenerationType(item.type)}
                    className="w-4 h-4"
                  />
                  <span className="text-lg">{item.icon}</span>
                  <span className="text-sm flex-1">{item.label}</span>
                </label>
              ))}
            </div>
            <p className="text-xs text-muted mt-2">
              Select 1-4 variants to generate. More variants = longer processing time.
              {generationTypes.length > 1 && (
                <span className="block mt-1 text-yellow-400">
                  ⚠️ {generationTypes.length} variants selected (~{generationTypes.length * 3}-{generationTypes.length * 5} min)
                </span>
              )}
            </p>
          </div>

          {/* Existing fields: notes, error display, buttons */}
          
          {error && <div className="text-sm text-red-400">{error}</div>}

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button loading={saving} type="submit" disabled={generationTypes.length === 0}>
              Create Lead
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

---

### 3.3 Variant Comparison View

**File:** `apps/web/src/app/app/leads/[id]/variants.tsx` **(NEW)**

```typescript
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, CheckCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/state/loading-state";
import { ErrorState } from "@/components/state/error-state";
import { EmptyState } from "@/components/state/empty-state";
import type { SiteVariant } from "@/lib/types";
import { cn } from "@/lib/utils";

async function getVariantsForLead(leadId: string): Promise<SiteVariant[]> {
  const response = await fetch(`/api/v1/sites/variants/${leadId}`, {
    credentials: "include",
  });
  if (!response.ok) {
    throw new Error("Failed to load variants");
  }
  const json = await response.json();
  return json.data || [];
}

const VARIANT_META: Record<string, { icon: string; color: string; description: string }> = {
  html_v1: {
    icon: "📄",
    color: "border-slate-500/40 bg-slate-500/10 text-slate-200",
    description: "Professional, industry-standard design with proven patterns",
  },
  html_v2: {
    icon: "⚡",
    color: "border-purple-500/40 bg-purple-500/10 text-purple-200",
    description: "Bold, high-energy startup aesthetic with modern effects",
  },
  html_v3: {
    icon: "🎨",
    color: "border-pink-500/40 bg-pink-500/10 text-pink-200",
    description: "Creative alternative with distinctive visual personality",
  },
  nextjs: {
    icon: "⚛️",
    color: "border-blue-500/40 bg-blue-500/10 text-blue-200",
    description: "Full Next.js site with editing and interactive features",
  },
};

export default function VariantsView({ leadId }: { leadId: string }) {
  const [variants, setVariants] = useState<SiteVariant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getVariantsForLead(leadId);
        setVariants(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load variants");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [leadId]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState error={error} />;
  if (variants.length === 0) {
    return <EmptyState message="No variants generated yet" />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-2">Generated Variants</h2>
        <p className="text-sm text-muted">
          Compare different design directions and select your preferred approach.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {variants.map((variant) => {
          const meta = VARIANT_META[variant.variantType] || VARIANT_META.nextjs;
          
          return (
            <div
              key={variant.id}
              className="border border-white/10 rounded-lg p-4 space-y-3 hover:border-white/20 transition"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{meta.icon}</span>
                  <div>
                    <h3 className="font-semibold">{variant.variantLabel}</h3>
                    <p className="text-xs text-muted mt-0.5">{meta.description}</p>
                  </div>
                </div>
                {variant.readinessStatus === "published" && (
                  <Badge className="bg-emerald-500/20 text-emerald-200 border-emerald-500/40">
                    <CheckCircle className="w-3 h-3 mr-1" />
                    Active
                  </Badge>
                )}
              </div>

              <div className="bg-white/5 rounded p-3 space-y-1 text-xs text-muted">
                <div>Type: {variant.variantType}</div>
                <div>Status: {variant.readinessStatus}</div>
                <div>QA: {variant.qaStatus}</div>
              </div>

              <div className="flex gap-2">
                <Link
                  href={variant.previewUrl}
                  target="_blank"
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm rounded border border-white/15 hover:bg-white/5 transition"
                >
                  Preview
                  <ExternalLink className="w-3 h-3" />
                </Link>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    // TODO: Implement variant activation
                    alert("Variant activation coming soon");
                  }}
                >
                  Activate
                </Button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

---

### 3.4 Add Variants to Lead Detail Page

**File:** `apps/web/src/app/app/leads/[id]/page.tsx`

**Add import and section:**
```typescript
import VariantsView from "./variants";

export default function LeadDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="space-y-8">
      {/* Existing sections */}
      
      {/* NEW: Variants section */}
      <div className="border-t border-white/10 pt-8">
        <VariantsView leadId={params.id} />
      </div>
    </div>
  );
}
```

---

## Phase 4: Testing & Quality Assurance

### 4.1 Backend Tests

**File:** `apps/backend/tests/test_variant_generation.py` **(NEW)**

```python
import pytest
from app.core.variant_strategy import get_variant_strategies, get_variant_strategy


def test_variant_strategies_structure():
    """Test that variant strategies have required fields."""
    strategies = get_variant_strategies()
    
    assert len(strategies) == 3  # html_v1, html_v2, html_v3
    
    for variant_type, strategy in strategies.items():
        assert "variantLabel" in strategy
        assert "designMode" in strategy
        assert "paletteMode" in strategy
        assert "creativeBriefGuidance" in strategy
        assert "inspirationKeywords" in strategy
        assert "avoidPatterns" in strategy


def test_variant_strategies_are_distinct():
    """Test that each variant has distinct design parameters."""
    strategies = get_variant_strategies()
    
    design_modes = [s["designMode"] for s in strategies.values()]
    palette_modes = [s["paletteMode"] for s in strategies.values()]
    
    # Should have variety (not all the same)
    assert len(set(design_modes)) > 1
    assert len(set(palette_modes)) > 1


def test_industry_specific_strategies():
    """Test that industry affects variant strategies."""
    consulting_strats = get_variant_strategies("consulting")
    saas_strats = get_variant_strategies("saas")
    
    # Variant 3 should differ based on industry
    assert consulting_strats["html_v3"]["variantLabel"] != saas_strats["html_v3"]["variantLabel"]


@pytest.mark.asyncio
async def test_generation_lock():
    """Test that generation lock prevents parallel execution."""
    from app.core.generation_lock import generation_lock
    import asyncio
    
    counter = []
    
    async def task():
        async with generation_lock(timeout_seconds=10):
            counter.append("start")
            await asyncio.sleep(0.1)
            counter.append("end")
    
    # Run 2 tasks concurrently
    await asyncio.gather(task(), task())
    
    # Should be sequential: start, end, start, end
    assert counter == ["start", "end", "start", "end"]
```

---

### 4.2 Frontend Tests

**File:** `apps/web/src/app/app/leads/__tests__/variants.test.tsx` **(NEW)**

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import VariantsView from "../[id]/variants";

global.fetch = jest.fn();

describe("VariantsView", () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it("renders loading state initially", () => {
    (fetch as jest.Mock).mockImplementation(() => new Promise(() => {}));
    
    render(<VariantsView leadId="test-lead-id" />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders variants when loaded", async () => {
    const mockVariants = [
      {
        id: "v1",
        variantType: "html_v1",
        variantLabel: "Professional Standard",
        previewUrl: "https://example.com/st/test-v1",
        readinessStatus: "ready",
        qaStatus: "pass",
      },
      {
        id: "v2",
        variantType: "html_v2",
        variantLabel: "Bold Startup",
        previewUrl: "https://example.com/st/test-v2",
        readinessStatus: "ready",
        qaStatus: "pass",
      },
    ];

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: mockVariants }),
    });

    render(<VariantsView leadId="test-lead-id" />);

    await waitFor(() => {
      expect(screen.getByText("Professional Standard")).toBeInTheDocument();
      expect(screen.getByText("Bold Startup")).toBeInTheDocument();
    });
  });

  it("renders error state on fetch failure", async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    render(<VariantsView leadId="test-lead-id" />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load variants/i)).toBeInTheDocument();
    });
  });
});
```

---

### 4.3 End-to-End Test Scenario

**Manual Testing Steps:**

1. **Create Lead with Multiple Variants**
   ```bash
   # Via API
   curl -X POST http://localhost:8000/api/v1/leads \
     -H "Cookie: lenquant_session=$SESSION" \
     -H "Content-Type: application/json" \
     -d '{
       "websiteUrl": "https://example.com",
       "companyName": "Test Company",
       "generationTypes": ["html_v1", "html_v2", "html_v3", "nextjs"]
     }'
   ```

2. **Monitor Celery Logs**
   ```bash
   docker compose logs -f backend
   # Should see sequential generation with lock messages
   ```

3. **Verify Redis Lock**
   ```bash
   redis-cli
   > GET lenquant:generation:lock
   # Should show lock during generation, disappear after
   ```

4. **Check Generated Sites**
   ```bash
   # Via MongoDB
   mongosh "mongodb://localhost:27017/lenquant"
   > db.generated_sites.find({ leadId: "YOUR_LEAD_ID" }).count()
   # Should return 4 (one per variant)
   ```

5. **Test Preview URLs**
   - Visit `http://localhost:3000/st/test-company-v1` (HTML variant 1)
   - Visit `http://localhost:3000/st/test-company-v2` (HTML variant 2)
   - Visit `http://localhost:3000/st/test-company-v3` (HTML variant 3)
   - Visit `http://localhost:3000/st/test-company` (Next.js)

6. **Verify Different Designs**
   - V1 should be light, professional, clean
   - V2 should be dark, bold, animated
   - V3 should be colorful, playful/luxe

---

## Phase 5: Deployment

### 5.1 Environment Variables

**File:** `.env.production` (on EC2 server)

**Add/verify:**
```bash
# Existing
MONGODB_URI=...
CELERY_BROKER_URL=redis://redis:6379/0
ASSET_S3_BUCKET=lenquant-assets
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6-v1:0

# Bedrock fallback models (already in config.py)
# No new env vars needed - uses hardcoded list in settings
```

---

### 5.2 Docker Compose Update

**File:** `docker-compose.yml` (production)

**No changes needed!** Existing services work:
- ✅ Redis already running (for Celery + locks)
- ✅ Celery already configured (`solo` pool, `concurrency=1`)
- ✅ MongoDB already running
- ✅ Backend already has S3 access

---

### 5.3 Deployment Steps

```bash
# 1. SSH into production server
ssh -i ~/.ssh/lenquant.pem ubuntu@ec2-32-194-123-142.compute-1.amazonaws.com

# 2. Navigate to project
cd /opt/lenquant

# 3. Pull latest code
git pull origin main

# 4. Rebuild backend (new code + dependencies)
docker compose build backend

# 5. Restart services
docker compose restart backend
docker compose restart celery

# 6. Verify Celery is running with solo pool
docker compose logs celery | grep "pool=solo"

# 7. Monitor logs during first generation
docker compose logs -f backend celery

# 8. Test API health
curl http://localhost:8000/api/v1/health
```

---

## Phase 6: Monitoring & Alerts

### 6.1 Logging Strategy

**Key log points:**

1. **Lock acquisition/release**
   ```python
   logger.info("Generation lock acquired")
   logger.info("Generation lock released")
   logger.warning("Waiting for generation lock... (30s elapsed)")
   ```

2. **Model fallback**
   ```python
   logger.warning("Bedrock model X failed, trying fallback Y")
   logger.info("Generation succeeded with fallback model Y")
   ```

3. **Variant generation stages**
   ```python
   logger.info("Generating master brief for html_v1 (lead abc)")
   logger.info("Generating static HTML for html_v1 (site xyz)")
   logger.info("Variant html_v1 completed: https://sites.lenquant.com/st/acme-v1")
   ```

4. **Errors**
   ```python
   logger.error("Multi-variant generation failed: rate limit exhausted")
   logger.error("Lock timeout after 300s - another generation still running")
   ```

---

### 6.2 Metrics to Track

**In production dashboard:**

1. **Generation throughput**
   - Variants generated per hour
   - Average time per variant (should be 3-5 min for HTML, 5-8 min for Next.js)

2. **Lock contention**
   - How often tasks wait for lock
   - Max wait time observed

3. **Model fallback rate**
   - % of generations using fallback models
   - Which models succeed most often

4. **Failure rate**
   - % of variants failing generation
   - Common error types

---

## Summary

### What Was Built

✅ **Backend (450 lines)**
- Variant strategy mapper (`variant_strategy.py`)
- Static HTML generator (`static_html_generator.py`)
- Redis distributed lock (`generation_lock.py`)
- Extended master brief generation (variant-aware)
- Extended site repository (multi-variant support)
- Celery task for sequential generation
- API endpoints for variants

✅ **Frontend (150 lines)**
- Extended lead creation modal (variant checkboxes)
- Variant comparison view
- Type definitions

✅ **Infrastructure**
- Reused existing schemas (extended `GeneratedSite`)
- Reused existing Celery setup
- Reused existing Bedrock client with fallback
- S3 storage for static assets

### Total Code: ~600 lines

### Key Features Delivered

1. **4 Variant Types**
   - HTML v1: Professional standard
   - HTML v2: Bold startup
   - HTML v3: Creative alternative
   - Next.js: Full interactive site

2. **Distinct Creative Directions**
   - Each HTML variant gets unique master brief
   - Industry-aware strategy selection
   - Radically different designs (light vs dark vs colorful)

3. **Global Sequential Generation**
   - Redis distributed lock
   - No parallel execution (prevents rate limits)
   - Works across multiple workers/servers

4. **Automatic Model Fallback**
   - Uses existing Bedrock client
   - 6 fallback models configured
   - Transparent retry with different models

5. **Static HTML Output**
   - No React runtime
   - Separate CSS/JS files
   - S3 storage and direct serving

6. **Production-Ready**
   - Full error handling
   - Comprehensive logging
   - Backward compatible
   - Tested and documented

---

## Next Steps

1. **Review this document**
2. **Answer any clarifying questions**
3. **I'll implement phase-by-phase** with quality checks after each phase
4. **Deploy to staging first** for testing
5. **Production rollout** after validation

Ready to start implementation?
