"""
Static HTML generation for multi-variant output.

Generates standalone HTML/CSS/JS files (no React runtime) from master brief.
"""

from __future__ import annotations

import json
import logging
import posixpath
import re
from typing import Any
from urllib.parse import urlsplit

import boto3
from bs4 import BeautifulSoup
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.compiler_client import get_compiler_client
from app.core.generation_policy import apply_brief_policy, brand_color_policy, enforce_html_testimonials, static_safety_css
from app.core.llm import get_llm_client
from app.core.verified_images import verified_image_catalog, enforce_image_catalog
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

    master_brief = apply_brief_policy(master_brief, extraction)
    images = await verified_image_catalog(extraction)
    prompt = _build_static_html_prompt(master_brief, extraction, variant_type)
    prompt += "\nVERIFIED SOURCE PHOTOGRAPHS (use only these exact URLs; match subjects to descriptions):\n" + json.dumps(images)
    prompt += "\nIf no appropriate photograph exists, use CSS shapes, typography and gradients. Do not invent project locations, team identities or image URLs."
    html_content = css_content = ""
    for attempt in range(2):
        response = await llm.generate_text(prompt=prompt, temperature=0.7, max_tokens=32768)
        try:
            html_content = _extract_complete_block(response, "html")
            css_content = _extract_complete_block(response, "css")
            if not re.search(r"</html\s*>", html_content, re.I):
                raise ValueError("HTML document is incomplete")
            break
        except ValueError as exc:
            if attempt == 1:
                raise
            logger.warning("Incomplete static design, retrying compact output: %s", exc)
            prompt += "\nPrevious output was incomplete. Reduce repetition and size; return complete HTML and CSS blocks under 18000 tokens total."

    # Reviews are rendered from extraction records rather than AI-written quotes.
    html_content = enforce_html_testimonials(html_content, extraction)
    html_content, css_content = enforce_image_catalog(html_content, css_content, images)
    document = BeautifulSoup(html_content, "html.parser")
    for script in list(document.find_all("script")):
        if script.get("type", "") not in {"application/ld+json", "application/json"}:
            script.decompose()
    html_content = str(document)
    css_content += "\n" + static_safety_css(extraction)

    # A separate bounded script response cannot be cut off by a large stylesheet.
    js_prompt = _build_javascript_prompt(html_content)
    js_content = ""
    for attempt in range(2):
        response = await llm.generate_text(prompt=js_prompt, temperature=0.3, max_tokens=8192)
        try:
            js_content = _extract_complete_block(response, "javascript")
            await get_compiler_client().validate_javascript(js_content)
            break
        except ValueError as exc:
            if attempt == 1:
                raise
            js_prompt += f"\nPrevious script was invalid: {str(exc)[:1000]}. Return a complete, concise script with all delimiters closed; stay under 4000 tokens."

    # Upload CSS and JS to S3
    settings = get_settings()
    logger.info(
        f"[DEBUG] S3 config: bucket={settings.asset_s3_bucket}, "
        f"prefix={settings.asset_s3_prefix}, region={settings.asset_s3_region}"
    )
    css_url = _upload_to_s3(
        content=css_content,
        filename=f"{site_id}/styles.css",
        content_type="text/css",
        bucket=settings.asset_s3_bucket,
        prefix=settings.asset_s3_prefix,
    )
    js_url = _upload_to_s3(
        content=js_content,
        filename=f"{site_id}/script.js",
        content_type="application/javascript",
        bucket=settings.asset_s3_bucket,
        prefix=settings.asset_s3_prefix,
    )
    logger.info(f"[DEBUG] S3 upload results: css_url={css_url}, js_url={js_url}")

    # Point generated local asset references at the uploaded files. A relative
    # "styles.css" on /st/{slug} resolves to /st/styles.css, not alongside the
    # generated page, and Next.js then returns an HTML 404 for the stylesheet.
    html_final = _attach_static_assets(
        html_content,
        css_url=css_url,
        js_url=js_url,
        css_content=css_content,
        js_content=js_content,
    )

    logger.info(
        f"[DEBUG] Final HTML length: {len(html_final)} (original: {len(html_content)})"
    )
    logger.info(f"Static HTML generated successfully for site {site_id}")

    return {
        "html": html_final,
        "cssUrl": css_url,
        "jsUrl": js_url,
    }


def _attach_static_assets(
    html: str,
    *,
    css_url: str | None,
    js_url: str | None,
    css_content: str,
    js_content: str,
) -> str:
    """Resolve generated local CSS/JS references and attach their contents.

    Generated HTML often includes its own ``styles.css`` and ``script.js``
    tags. Rewriting those tags avoids broken relative URLs on nested preview
    routes and avoids loading each asset twice.
    """

    html, css_attached = _rewrite_asset_tags(
        html,
        tag_name="link",
        attribute="href",
        filename="styles.css",
        remote_url=css_url,
        content=css_content,
    )
    html, js_attached = _rewrite_asset_tags(
        html,
        tag_name="script",
        attribute="src",
        filename="script.js",
        remote_url=js_url,
        content=js_content,
    )

    if not css_attached:
        css_tag = (
            f'<link rel="stylesheet" href="{css_url}">'
            if css_url
            else f"<style>\n{css_content}\n</style>"
        )
        html = _insert_before_or_append(html, "</head>", css_tag)

    if not js_attached:
        js_tag = (
            f'<script src="{js_url}" defer></script>'
            if js_url
            else f"<script>\n{js_content}\n</script>"
        )
        html = _insert_before_or_append(html, "</body>", js_tag)

    return html


def _rewrite_asset_tags(
    html: str,
    *,
    tag_name: str,
    attribute: str,
    filename: str,
    remote_url: str | None,
    content: str,
) -> tuple[str, bool]:
    """Rewrite references to a generated local asset, if one is present."""

    tag_pattern = re.compile(
        r"<script\b[^>]*>.*?</script\s*>" if tag_name == "script" else r"<link\b[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    attribute_pattern = re.compile(
        rf"\b{attribute}\s*=\s*(?:(['\"])(.*?)\1|([^\s>]+))",
        re.IGNORECASE,
    )
    attached = False

    def replace_tag(match: re.Match[str]) -> str:
        nonlocal attached
        tag = match.group(0)
        attr_match = attribute_pattern.search(tag)
        if not attr_match:
            return tag

        source = attr_match.group(2) if attr_match.group(1) else attr_match.group(3)
        if source != remote_url and not _is_local_asset_reference(source, filename):
            return tag

        if attached:
            return ""
        attached = True
        if remote_url:
            quote = attr_match.group(1) or '"'
            return (
                tag[: attr_match.start()]
                + f"{attribute}={quote}{remote_url}{quote}"
                + tag[attr_match.end() :]
            )

        inline_tag = "style" if tag_name == "link" else "script"
        safe_content = re.sub(r"</script", r"<\\/script", content, flags=re.I) if inline_tag == "script" else content
        return f"<{inline_tag}>\n{safe_content}\n</{inline_tag}>"

    return tag_pattern.sub(replace_tag, html), attached


def _is_local_asset_reference(source: str, filename: str) -> bool:
    """Match only local references to the generated asset, not remote files."""
    parsed = urlsplit(source.strip())
    if parsed.scheme or parsed.netloc:
        return False
    basename = posixpath.basename(parsed.path)
    return basename == filename or basename.endswith(posixpath.splitext(filename)[1])


def _insert_before_or_append(html: str, closing_tag: str, content: str) -> str:
    match = re.search(re.escape(closing_tag), html, re.IGNORECASE)
    if not match:
        return f"{html}\n{content}"
    return f"{html[:match.start()]}{content}\n{html[match.start():]}"


def _build_static_html_prompt(
    brief: MasterBrief,
    extraction: ExtractionSnapshot,
    variant_type: str,
) -> str:
    """Build LLM prompt for static HTML generation."""
    # Build sections summary
    extracted_testimonials = [
        testimonial
        for testimonial in extraction.extractedTestimonials
        if testimonial.quote.strip()
    ]
    brief_sections = [
        section
        for section in brief.sections
        if extracted_testimonials
        or not any(
            term in " ".join(
                [
                    section.purpose,
                    section.headline,
                    section.suggestedApproach,
                    section.contentSummary,
                    *section.contentPoints,
                ]
            ).casefold()
            for term in (
                "testimonial",
                "customer quote",
                "client quote",
                "review",
                "endorsement",
            )
        )
    ]
    sections_summary = "\n".join(
        f"  - {s.purpose}: {s.headline}" for s in brief_sections[:7]
    )

    if extracted_testimonials:
        testimonial_policy = (
            "TESTIMONIAL EVIDENCE (USE EXACTLY; NEVER INVENT):\n"
            "Only the extracted testimonials below may appear. Reproduce each "
            "quote verbatim. Do not rewrite, combine, invent quotes, ratings, "
            "results, names, or company details. Only use author details listed "
            "on that same record.\n"
            + "\n".join(
                f"- Quote: {testimonial.quote!r}; "
                f"authorName: {testimonial.authorName or 'not extracted'}; "
                f"authorTitle: {testimonial.authorTitle or 'not extracted'}; "
                f"authorCompany: {testimonial.authorCompany or 'not extracted'}"
                for testimonial in extracted_testimonials
            )
        )
    else:
        testimonial_policy = (
            "TESTIMONIAL EVIDENCE (NONE FOUND): The extraction contains no "
            "testimonials. Do not create a testimonial, review, customer quote, "
            "endorsement, rating, or testimonial section. Ignore any brief "
            "recommendation for one. Other proof may only use facts explicitly "
            "supported by extracted source content."
        )

    # Get brand info
    logo_url = brief.brandAssets.logoUrl or "None"
    primary_color = brief.brandAssets.primaryColor or "#000000"
    secondary_color = brief.brandAssets.secondaryColor or "#666666"
    font_family = brief.brandAssets.fontFamily or "system-ui, sans-serif"

    # Get company name
    company_name = extraction.summary.companyName or (urlsplit(extraction.canonicalWebsiteUrl or "").hostname or "Company")
    # Kept outside the f-string so pyright doesn't misparse the JS object literal syntax
    _animation_notes = (
        "Scroll-triggered animations using IntersectionObserver — important rules:\n"
        "   - NEVER set opacity:0 in CSS directly. Only hide elements by adding a class via JS "
        "(e.g. add 'js-loaded' to <html> first, then use '.js-loaded .animate-on-scroll { opacity:0 }') "
        "so content is always fully visible if JS fails or is slow.\n"
        "   - Hero/above-the-fold elements must never be hidden by opacity, visibility, clip-path, scale, masks, or transforms — always visible on load.\n"
        "   - Number counters must animate to their final value; always set the final number as a "
        "fallback in case the animation does not trigger."
    )

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
- Sections:
{sections_summary}
- CTA Strategy: {brief.ctaStrategy}

{testimonial_policy}

BRAND ASSETS:
- Company Name: {company_name}
- Logo URL: {logo_url}
- Primary Color: {primary_color}
- Secondary Color: {secondary_color}
- Font Family: {font_family}

{brand_color_policy(extraction)}

VARIANT TYPE: {variant_type}

REQUIREMENTS:
1. Generate TWO separate code blocks; JavaScript is generated separately:
   - HTML: Complete semantic HTML5 structure
   - CSS: All styles in a single stylesheet
   - Keep the total response under 20000 tokens; avoid repetitive CSS and verbose comments.

2. HTML Structure:
   - Semantic tags (<header>, <main>, <section>, <footer>)
   - Mark the hero headline with data-hero-headline and primary CTA links/buttons with data-primary-cta
   - No testimonial/review markup: verified testimonial cards are inserted from extraction records by the renderer
   - Proper meta tags (viewport, description, title)
   - Accessibility: ARIA labels, alt text, semantic structure
   - Include all listed sections, subject to the testimonial evidence rule above
   - Use brand logo if available (as img src)
   - NO inline styles or scripts
   - Use only the verified source photograph URLs supplied below. Never invent or guess image URLs.
   - Keep the native cursor visible everywhere. Never use cursor:none or a replacement custom cursor.

3. CSS Requirements:
   - Use CSS custom properties for colors/spacing
   - Responsive design (mobile-first with media queries)
   - Smooth animations matching motion level
   - Follow the creative direction's color mood and typography
   - Include hover states for interactive elements
   - Modern CSS (flexbox, grid)

4. JavaScript Requirements:
   - Vanilla JS only (no jQuery, no React, no frameworks)
   - Smooth scroll behavior for anchor links
   - Mobile menu toggle
   - {_animation_notes}
   - Form validation if contact form present

5. Design Quality:
   - Match the visual style and creative direction
   - Implement the design concept prominently
   - The source brand color rule takes precedence over the creative color strategy
   - Typography should reflect the personality described
   - Professional, polished appearance

OUTPUT FORMAT:
Return your response in this exact format (two complete, closed code blocks):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="...">
    <title>...</title>
</head>
<body>
    ...complete HTML here...
</body>
</html>
```

```css
/* styles.css */
:root {{
  --primary-color: {primary_color};
  --secondary-color: {secondary_color};
}}
...complete CSS here...
```



Generate high-quality, production-ready code that implements this brief faithfully.
"""


def _extract_complete_block(response: str, language: str) -> str:
    languages = r"(?:javascript|js)" if language == "javascript" else re.escape(language)
    match = re.search(rf"```{languages}\s*\n(.*?)\n```", response, re.DOTALL | re.IGNORECASE)
    if not match:
        raise ValueError(f"No {language.upper()} code block or truncated block")
    content = match.group(1).strip()
    if not content:
        raise ValueError(f"Empty {language} code block")
    return content


def _parse_llm_response(response: str) -> tuple[str, str, str]:
    """Legacy three-block parser: incomplete assets must never be published."""
    return tuple(_extract_complete_block(response, lang) for lang in ("html", "css", "javascript"))


def _build_javascript_prompt(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    manifest = [{"tag": node.name, "attributes": node.attrs}
                for node in soup.find_all(True) if node.name not in {"meta", "link", "script", "style"}]
    return """Generate concise, complete vanilla browser JavaScript for this DOM.
Return ONE closed ```javascript code block. Do not output HTML or CSS.
Implement mobile navigation, form validation, anchor scrolling, and optional scroll enhancements.
Use only selectors that exist in the DOM inventory. Null-check elements and optional browser APIs.
Use a deferred script; initialize when DOM is ready, including when DOMContentLoaded already fired.
Hero text is always visible. Never hide h1, its words, or any above-the-fold content.
Scroll animation must use progressive enhancement and leave final content visible if anything fails.
Respect prefers-reduced-motion. Do not add testimonials, star ratings, fake counters, or unsupported claims.
Keep all interactions within 4000 tokens and close every function, string, and delimiter.
DOM inventory:
""" + json.dumps(manifest, ensure_ascii=False)


def _upload_to_s3(
    content: str,
    filename: str,
    content_type: str,
    bucket: str | None,
    prefix: str,
) -> str | None:
    """Upload file to S3 and return public URL."""

    if not bucket:
        logger.warning("S3 bucket not configured (ASSET_S3_BUCKET), skipping upload")
        return None

    settings = get_settings()

    try:
        s3_client = boto3.client("s3", region_name=settings.asset_s3_region)

        key = f"{prefix}static-sites/{filename}"

        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content.encode("utf-8"),
            ContentType=content_type,
            CacheControl="public, max-age=3600",
        )

        # Return CDN URL
        url = f"https://{bucket}.s3.amazonaws.com/{key}"

        logger.info(f"Uploaded {content_type} to S3: {url}")

        return url

    except ClientError as e:
        logger.error(f"Failed to upload to S3: {e}")
        return None
