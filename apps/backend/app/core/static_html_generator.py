"""
Static HTML generation for multi-variant output.

Generates standalone HTML/CSS/JS files (no React runtime) from master brief.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import boto3
from botocore.exceptions import ClientError

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
    logger.info(f"Generating static HTML for variant {variant_type} (site {site_id})")
    response = await llm.generate_text(
        prompt=prompt,
        temperature=0.7,
        max_tokens=32768,  # Increased to maximum to avoid truncation
    )

    # Debug: Log response metadata
    logger.info(
        f"[DEBUG] LLM response received for {variant_type}: "
        f"length={len(response)}, first_200_chars={response[:200]}"
    )

    # Debug: Check for code block markers
    html_start = response.find("```html")
    html_end = response.find("```", html_start + 7) if html_start >= 0 else -1
    css_start = response.find("```css")
    css_end = response.find("```", css_start + 6) if css_start >= 0 else -1
    js_start = response.find("```javascript")
    if js_start < 0:
        js_start = response.find("```js")
    logger.info(
        f"[DEBUG] Code block positions: html_start={html_start}, html_end={html_end}, "
        f"css_start={css_start}, css_end={css_end}, js_start={js_start}"
    )
    if html_start >= 0:
        # Log 100 chars after ```html marker to see what follows
        logger.info(
            f"[DEBUG] After ```html marker: {repr(response[html_start : html_start + 100])}"
        )
    if css_start >= 0:
        logger.info(
            f"[DEBUG] After ```css marker: {repr(response[css_start : css_start + 100])}"
        )

    # Parse response
    try:
        html_content, css_content, js_content = _parse_llm_response(response)
        logger.info(
            f"[DEBUG] Parsed successfully: "
            f"html_len={len(html_content)}, css_len={len(css_content)}, js_len={len(js_content)}"
        )
    except ValueError as e:
        logger.error(f"[DEBUG] Parsing failed: {e}")
        logger.error(f"[DEBUG] Response starts with: {repr(response[:150])}")
        if html_start >= 0 and html_end >= 0:
            logger.error(f"[DEBUG] HTML block length would be: {html_end - html_start}")
        raise

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

    # Inject CSS/JS URLs into HTML
    html_final = html_content
    if css_url:
        html_final = html_final.replace(
            "</head>", f'<link rel="stylesheet" href="{css_url}">\n</head>'
        )
    if js_url:
        html_final = html_final.replace(
            "</body>", f'<script src="{js_url}"></script>\n</body>'
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


def _build_static_html_prompt(
    brief: MasterBrief,
    extraction: ExtractionSnapshot,
    variant_type: str,
) -> str:
    """Build LLM prompt for static HTML generation."""
    # Build sections summary
    sections_summary = "\n".join(
        f"  - {s.purpose}: {s.headline}" for s in brief.sections[:7]
    )

    # Get brand info
    logo_url = brief.brandAssets.logoUrl or "None"
    primary_color = brief.brandAssets.primaryColor or "#000000"
    secondary_color = brief.brandAssets.secondaryColor or "#666666"
    font_family = brief.brandAssets.fontFamily or "system-ui, sans-serif"

    # Get company name
    company_name = extraction.summary.companyName or "Company"

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

BRAND ASSETS:
- Company Name: {company_name}
- Logo URL: {logo_url}
- Primary Color: {primary_color}
- Secondary Color: {secondary_color}
- Font Family: {font_family}

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
   - Use brand logo if available (as img src)
   - NO inline styles or scripts
   - Use placeholder image URLs from https://images.unsplash.com for any images

3. CSS Requirements:
   - Use CSS custom properties for colors/spacing
   - try to avoid opacity:0 if the elements dont have a clear animation or a reason to be hidden
   - Responsive design (mobile-first with media queries)
   - Smooth animations matching motion level
   - Follow the creative direction's color mood and typography
   - Include hover states for interactive elements
   - Modern CSS (flexbox, grid)

4. JavaScript Requirements:
   - Vanilla JS only (no jQuery, no React, no frameworks)
   - Smooth scroll behavior for anchor links
   - Mobile menu toggle
   - Scroll-triggered fade-in animations using IntersectionObserver — elements MUST use `observer.observe()` and transition from opacity:0 to opacity:1 when they enter the viewport. Always initialize the IntersectionObserver with `{threshold: 0.1 }` so elements trigger early. Elements above the fold (hero) must start at opacity:1, NOT opacity:0.
   - Form validation if contact form present

5. Design Quality:
   - Match the visual style and creative direction
   - Implement the design concept prominently
   - Use the specified color strategy
   - Typography should reflect the personality described
   - Professional, polished appearance

OUTPUT FORMAT:
Return your response in this exact format (three code blocks):

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

    # Extract HTML - try multiple patterns with increasing leniency
    html_match = None
    # Pattern 1: Standard with explicit newline
    html_match = re.search(r"```html\s*\n(.*?)\n```", response, re.DOTALL)
    if not html_match:
        # Pattern 2: Any whitespace after marker
        html_match = re.search(r"```html\s+(.*?)```", response, re.DOTALL)
    if not html_match:
        # Pattern 3: No whitespace requirement, greedy
        html_match = re.search(r"```html(.*?)```", response, re.DOTALL)
    if not html_match:
        # Pattern 4: Manual extraction if markers exist
        html_start_pos = response.find("```html")
        html_end_pos = (
            response.find("```", html_start_pos + 7) if html_start_pos >= 0 else -1
        )
        if html_start_pos >= 0 and html_end_pos >= 0:
            html = response[html_start_pos + 7 : html_end_pos].strip()
            logger.info(f"[DEBUG] Manual HTML extraction: {len(html)} chars")
        else:
            raise ValueError("No HTML code block found in LLM response")
    else:
        html = html_match.group(1).strip()

    # Extract CSS - same pattern approach with truncation handling
    css_match = None
    css_match = re.search(r"```css\s*\n(.*?)\n```", response, re.DOTALL)
    if not css_match:
        css_match = re.search(r"```css\s+(.*?)```", response, re.DOTALL)
    if not css_match:
        css_match = re.search(r"```css(.*?)```", response, re.DOTALL)
    if not css_match:
        # Pattern 4: Manual extraction if markers exist
        css_start_pos = response.find("```css")
        if css_start_pos >= 0:
            css_end_pos = response.find("```", css_start_pos + 6)
            if css_end_pos >= 0:
                css = response[css_start_pos + 6 : css_end_pos].strip()
                logger.info(f"[DEBUG] Manual CSS extraction: {len(css)} chars")
            else:
                # CSS block started but no closing marker (truncated response)
                # Take everything from CSS start to end of response
                css = response[css_start_pos + 6 :].strip()
                logger.warning(
                    f"[DEBUG] CSS truncated (no closing marker), extracted {len(css)} chars"
                )
        else:
            raise ValueError("No CSS code block found in LLM response")
    else:
        css = css_match.group(1).strip()

    # Extract JS - same pattern approach with truncation handling
    js_match = None
    js_match = re.search(r"```(?:javascript|js)\s*\n(.*?)\n```", response, re.DOTALL)
    if not js_match:
        js_match = re.search(r"```(?:javascript|js)\s+(.*?)```", response, re.DOTALL)
    if not js_match:
        js_match = re.search(r"```(?:javascript|js)(.*?)```", response, re.DOTALL)
    if not js_match:
        # Pattern 4: Manual extraction if markers exist
        js_start_pos = response.find("```javascript")
        if js_start_pos < 0:
            js_start_pos = response.find("```js")
            js_marker_len = 5 if js_start_pos >= 0 else 0
        else:
            js_marker_len = 13
        if js_start_pos >= 0:
            js_end_pos = response.find("```", js_start_pos + js_marker_len)
            if js_end_pos >= 0:
                js = response[js_start_pos + js_marker_len : js_end_pos].strip()
                logger.info(f"[DEBUG] Manual JS extraction: {len(js)} chars")
            else:
                # JS block started but no closing marker (truncated)
                js = response[js_start_pos + js_marker_len :].strip()
                logger.warning(
                    f"[DEBUG] JS truncated (no closing marker), extracted {len(js)} chars"
                )
        else:
            logger.warning("No JavaScript code block found, using minimal JS")
            js = "// Minimal script\ndocument.addEventListener('DOMContentLoaded', () => {});"
    else:
        js = js_match.group(1).strip()

    return html, css, js


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
