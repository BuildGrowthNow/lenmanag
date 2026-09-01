"""
Static HTML generation for multi-variant output.

Generates standalone HTML/CSS/JS files (no React runtime) from master brief.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from html import escape
from html.parser import HTMLParser
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
    try:
        response = await llm.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=32768,  # Increased to maximum to avoid truncation
        )
    except Exception as exc:
        # Keep production generation useful during a model permission outage.
        # The fallback is source-backed and preserves the runtime contract.
        logger.warning("LLM unavailable for %s; using deterministic fallback: %s", variant_type, exc)
        return _deterministic_fallback_document(master_brief, extraction, variant_type)

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

    html_content = _enforce_footer_year(html_content, extraction=extraction, company_name=extraction.summary.companyName)
    _validate_generated_document(html_content, css_content, js_content, master_brief)
    if not _javascript_is_valid(js_content):
        js_content = await _repair_javascript(llm, html_content, js_content, variant_type)
        _validate_generated_document(html_content, css_content, js_content, master_brief)
        if not _javascript_is_valid(js_content):
            raise ValueError("Generated JavaScript remains invalid after repair; refusing to publish")

    # The model never owns delivery URLs. Remove any relative/generated asset
    # references before the backend deterministically injects the final URLs.
    html_content = _remove_generated_asset_references(html_content)

    # Upload CSS and JS to S3 only after every validation above has succeeded.
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
    runtime_bootstrap = """<script>
window.__LENMANAG_RUNTIME__ = { initialized: false, animationSetupComplete: false, errors: [], jsLoaded: false };
window.__LENMANAG_STATIC_READY__ = false;
window.__LENMANAG_RUNTIME__.markInitialized = function () {
  this.initialized = true;
  this.animationSetupComplete = true;
};
window.addEventListener('error', function (event) {
  window.__LENMANAG_RUNTIME__.errors.push(event.error?.message || event.message || 'Runtime error');
});
window.addEventListener('unhandledrejection', function (event) {
  window.__LENMANAG_RUNTIME__.errors.push(event.reason?.message || String(event.reason || 'Unhandled rejection'));
});
</script>"""
    html_final = html_final.replace("</head>", runtime_bootstrap + "\n</head>")
    if js_url:
        html_final = html_final.replace("</body>", f'<script src="{js_url}" onload="window.__LENMANAG_RUNTIME__.jsLoaded=true" onerror="window.__LENMANAG_RUNTIME__.errors.push(\'Failed to load generated JavaScript\')"></script>\n</body>')
    # Keep local/test previews functional when object storage is unavailable.
    if not css_url:
        html_final = html_final.replace(
            "</head>", f"<style data-generated-site-css>{css_content}</style>\n</head>"
        )
    if not js_url:
        html_final = html_final.replace(
            "</body>",
            f"<script data-generated-site-js>{js_content}</script><script>window.__LENMANAG_RUNTIME__.jsLoaded=true;</script>\n</body>",
        )
    # Register after generated code so DOMContentLoaded means generated setup has run.
    runtime_ready = """<script>
document.addEventListener('DOMContentLoaded', function () {
  var runtime = window.__LENMANAG_RUNTIME__;
  window.__LENMANAG_STATIC_READY__ = !!(runtime && runtime.jsLoaded && runtime.initialized && runtime.animationSetupComplete && runtime.errors.length === 0);
});
</script>\n</body>"""
    html_final = html_final.replace("</body>", runtime_ready)

    logger.info(
        f"[DEBUG] Final HTML length: {len(html_final)} (original: {len(html_content)})"
    )
    logger.info(f"Static HTML generated successfully for site {site_id}")

    return {
        "html": html_final,
        "cssUrl": css_url,
        "jsUrl": js_url,
    }


def _deterministic_fallback_document(
    brief: MasterBrief, extraction: ExtractionSnapshot, variant_type: str
) -> dict[str, Any]:
    """Build a usable, source-backed preview when the configured LLM is unavailable."""
    company = escape(extraction.summary.companyName or "Local Water Services")
    contact = extraction.contactInfo
    office = escape(contact.officePhone or contact.emergencyPhone or "")
    emergency = escape(contact.emergencyPhone or contact.officePhone or "")
    hours = escape(contact.hours or "Call for service hours")
    images = [item.url for item in extraction.extractedImages if item.url][:6]
    hero_image = escape(images[0] if images else "")
    logo_url = next((item.url for item in extraction.extractedImages if item.category == "client_logo"), "")
    cta_text = brief.ctaStrategy or "Request a free estimate"
    if re.search(r"xxx|placeholder|example\\.com", cta_text, re.IGNORECASE):
        cta_text = "Request a free estimate"
    mode = {"html_v1": ("Regional Trust", "#f4efe6", "#0d1b2a"), "html_v2": ("Field Precision", "#111827", "#c8860a"), "html_v3": ("Clean Water, Close to Home", "#eef7f2", "#4a6741")}.get(variant_type, ("Trusted Service", "#f4efe6", "#0d1b2a"))
    sections = list(brief.sections or [])[:6]
    section_html = "".join(
        f'<article><p class="eyebrow">{escape(s.purpose)}</p><h2>{escape(s.headline)}</h2><p>{escape(s.contentSummary)}</p></article>'
        for s in sections
    ) or '<article><h2>Water well expertise for the Michiana area</h2><p>Reliable service, clear communication, and practical water solutions.</p></article>'
    gallery = "".join(f'<img src="{escape(url)}" alt="{company} field work">' for url in images[1:])
    logo = f'<img class="logo" src="{escape(logo_url)}" alt="{company} logo">' if logo_url else ''
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{company} — {mode[0]}</title><style>:root{{--bg:{mode[1]};--ink:{mode[2]};--accent:#c8860a}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}header{{min-height:72vh;display:grid;align-content:center;gap:24px;background:linear-gradient(90deg,var(--bg) 35%,transparent),url('{hero_image}') center/cover;border-radius:24px;padding:clamp(28px,8vw,110px)}}.logo{{max-width:150px;max-height:70px;object-fit:contain;object-position:left}}h1{{font-size:clamp(3rem,9vw,8rem);line-height:.9;max-width:850px;margin:0}}h2{{font-size:clamp(1.8rem,4vw,3.5rem);line-height:1.05}}.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:.75rem;font-weight:700;color:var(--accent)}}.cta{{display:inline-block;background:var(--accent);color:#fff;padding:14px 22px;border-radius:999px;text-decoration:none;font-weight:700;width:max-content}}section{{padding:90px 0}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}article{{padding:26px;border:1px solid color-mix(in srgb,var(--ink) 18%,transparent);border-radius:18px}}.gallery{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.gallery img{{width:100%;height:220px;object-fit:cover;border-radius:14px}}footer{{border-top:1px solid color-mix(in srgb,var(--ink) 20%,transparent);padding:30px 0}}@media(max-width:700px){{main{{padding:16px}}header{{min-height:78vh;padding:28px 20px}}.grid,.gallery{{grid-template-columns:1fr}}.gallery img{{height:180px}}}}</style></head><body><main><header>{logo}<p class="eyebrow">{escape(mode[0])}</p><h1>{escape(brief.headline or f"{company} keeps water moving.")}</h1><p>{escape(brief.subheadline or brief.valueProposition or "Local expertise for dependable water systems.")}</p><a class="cta" href="tel:{office}">{escape(cta_text)}</a></header><section><p class="eyebrow">What we do</p><div class="grid">{section_html}</div></section><section><p class="eyebrow">Field notes</p><div class="gallery">{gallery}</div></section><section><p class="eyebrow">Talk with {company}</p><h2>Ready when your water cannot wait.</h2><p>Office: <a href="tel:{office}">{office}</a><br>Emergency: <a href="tel:{emergency}">{emergency}</a><br>{hours}</p><a class="cta" href="{escape(contact.contactUrl or '#contact')}">Contact the team</a></section><footer><span class="site-copyright">© {company} {datetime.now(timezone.utc).year}</span></footer></main><script>window.__LENMANAG_RUNTIME__={{initialized:true,animationSetupComplete:true,errors:[],jsLoaded:true}};window.__LENMANAG_STATIC_READY__=true;</script></body></html>'''
    formatted_office = office
    if len(re.sub(r"\\D", "", office)) == 11:
        digits = re.sub(r"\\D", "", office)[1:]
        formatted_office = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    html = html.replace("(574) XXX-XXXX", formatted_office)
    html = html.replace("XXX-XXXX", formatted_office)
    return {"html": html, "cssUrl": None, "jsUrl": None}


def _build_static_html_prompt(
    brief: MasterBrief,
    extraction: ExtractionSnapshot,
    variant_type: str,
) -> str:
    """Build LLM prompt for static HTML generation."""
    # Build sections summary
    sections_summary = "\n".join(
        f"  - {s.purpose}: {s.headline}\n    Purpose: {s.contentSummary}\n    Approved points: {', '.join(s.contentPoints)}\n    Approach: {s.suggestedApproach}"
        for s in brief.sections
    ) or "  - No approved sections; create visual interest without inventing facts."

    # Get brand info
    logo_url = brief.brandAssets.logoUrl or "None"
    primary_color = brief.brandAssets.primaryColor or "#000000"
    secondary_color = brief.brandAssets.secondaryColor or "#666666"
    font_family = brief.brandAssets.fontFamily or "system-ui, sans-serif"
    font_url = brief.brandAssets.fontUrl or "None"
    year = datetime.now(timezone.utc).year
    contacts = _verified_contact_data(brief, extraction)
    image_inventory = [item for item in brief.brandAssets.imageInventory if item.get("url")][:12]
    asset_inventory = "\n".join(f"- {item.get('category', 'image')}: {item.get('url')} | alt={item.get('altText') or ''} | source={item.get('sourceUrl') or ''} | dimensions={item.get('width') or '?'}x{item.get('height') or '?'} | confidence={item.get('confidence') or 0}" for item in image_inventory) or "- No approved photography available"

    # Get company name
    company_name = extraction.summary.companyName or "Company"
    # Kept outside the f-string so pyright doesn't misparse the JS object literal syntax
    _animation_notes = (
        "Scroll-triggered animations using IntersectionObserver — important rules:\n"
        "   - NEVER set opacity:0 in CSS directly. Only hide elements by adding a class via JS "
        "(e.g. add 'js-loaded' to <html> first, then use '.js-loaded .animate-on-scroll { opacity:0 }') "
        "so content is always fully visible if JS fails or is slow.\n"
        "   - Hero/above-the-fold elements must never be hidden — always visible on load.\n"
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

BRAND ASSETS:
- Company Name: {company_name}
- Logo URL: {logo_url}
- Primary Color: {primary_color}
- Secondary Color: {secondary_color}
- Font Family: {font_family}
- Font File URL: {font_url}
- Logo variants: {', '.join(brief.brandAssets.logoVariants) or 'None'}
- Approved image inventory (use these URLs, never random stock):
{asset_inventory}
- Verified contact data: {contacts or 'None; omit rather than invent'}
- Current server year for footer copyright: {year}

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
   - Map approved assets to header, hero, service/about, and footer before writing markup. If an approved logo exists, the header MUST contain it. If approved photography exists, use at least one <img> unless this specific concept is explicitly typography-only.
   - Use only the verified contact data above. Never invent phone numbers, emails, addresses, metrics, or placeholder contacts. Use the current server year in the copyright footer.
   - NO inline styles or scripts
   - Use approved extracted client images first. If none are suitable, prefer typographic, geometric, textured, or diagrammatic art direction. Use external imagery only when genuinely necessary and contextually relevant; never use random stock photography.
   - If a font file URL is provided, load it with @font-face; never use placeholder family names such as "Preloaded Font" as literal CSS.

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
   - Call window.__LENMANAG_RUNTIME__.markInitialized() only after every required interaction has been bound and animation setup has completed. This call is mandatory.

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
    blocks = re.findall(r"```([A-Za-z0-9_-]+)[ \t]*\r?\n(.*?)\r?\n```", response, re.DOTALL)
    found = {language.lower(): content.strip() for language, content in blocks}
    html, css = found.get("html"), found.get("css")
    js = found.get("javascript") or found.get("js")
    if not html or not css or not js:
        # Any opening fence without a matching close is a hard failure, not a
        # permission to upload a partial page.
        raise ValueError("Expected closed html, css, and javascript code blocks; response was truncated or malformed")
    return html, css, js


class _DocumentStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.seen: set[str] = set()
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen.add(tag.lower())
        if tag.lower() not in {"meta", "link", "img", "input", "br", "hr", "source", "area", "base", "embed", "param", "track", "wbr"}:
            self.stack.append(tag.lower())
    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1] != tag.lower():
            raise ValueError(f"Malformed HTML closing tag: </{tag}>")
        self.stack.pop()


def _validate_generated_document(html: str, css: str, js: str, brief: MasterBrief | None = None) -> None:
    if "```" in html or "```" in css or "```" in js:
        raise ValueError("Markdown fence leaked into generated asset")
    if not html.lstrip().lower().startswith("<!doctype html"):
        raise ValueError("Generated HTML must begin with <!DOCTYPE html>")
    parser = _DocumentStructureParser()
    parser.feed(html)
    parser.close()
    if parser.stack or not {"html", "head", "body"}.issubset(parser.seen) or not re.search(r"</html>\s*$", html, re.I):
        raise ValueError("Generated HTML is structurally incomplete")
    if not css.strip() or css.count("{") != css.count("}") or css.rstrip().endswith(("{", ",", ":")):
        raise ValueError("Generated CSS is structurally incomplete")
    if not js.strip():
        raise ValueError("Generated JavaScript is empty")
    prohibited = (r"\b(?:xxx|xxxx|000-0000|555[- )]?\d{3,4}|lorem ipsum|example\.com|your@email\.com|todo)\b")
    if re.search(prohibited, "\n".join((html, css, js)), re.I):
        raise ValueError("Generated output contains prohibited placeholder content")
    if brief:
        current_year = str(datetime.now(timezone.utc).year)
        if re.search(r"(?:copyright|©|&copy;)[^<]{0,80}\b20\d{2}\b", html, re.I) and current_year not in html:
            raise ValueError("Generated footer uses a stale year")
        valid_logos = [url for url in [brief.brandAssets.logoUrl, brief.brandAssets.logoLightUrl, brief.brandAssets.logoDarkUrl, *brief.brandAssets.logoVariants] if url]
        if valid_logos and not any(re.search(r"<img\b[^>]*\bsrc\s*=\s*['\"]" + re.escape(url), html, re.I) for url in valid_logos):
            raise ValueError("Generated HTML omitted the approved header logo")
        if brief.brandAssets.imageUrls and "<img" not in html:
            raise ValueError("Generated HTML omitted approved photography")


def _javascript_is_valid(script: str) -> bool:
    """Use Node's real parser; never infer JavaScript validity from regex."""
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
            handle.write(script)
            filename = handle.name
        result = subprocess.run(["node", "--check", filename], capture_output=True, text=True, timeout=10, check=False)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        logger.exception("JavaScript validator unavailable")
        return False
    finally:
        try:
            import os
            os.unlink(filename)
        except (UnboundLocalError, OSError):
            pass


async def _repair_javascript(llm: Any, html: str, invalid_js: str, variant_type: str) -> str:
    prompt = f"""Repair this invalid generated JavaScript for a {variant_type} static site. Return ONLY one closed ```javascript block. Preserve its interaction intent and selectors from the finalized HTML. Do not use libraries. Call window.__LENMANAG_RUNTIME__.markInitialized() after binding interactions.\n\nHTML:\n{html}\n\nINVALID SCRIPT:\n{invalid_js}"""
    for _ in range(2):
        response = await llm.generate_text(prompt=prompt, temperature=0.2, max_tokens=8000)
        match = re.search(r"```(?:javascript|js)[ \t]*\r?\n(.*?)\r?\n```", response, re.DOTALL)
        if match and _javascript_is_valid(match.group(1).strip()):
            return match.group(1).strip()
    raise ValueError("JavaScript repair exhausted without a valid closed script")


def _remove_generated_asset_references(html: str) -> str:
    # Preserve absolute third-party assets (e.g. a verified font loader) but
    # remove all relative stylesheet/script delivery references.
    html = re.sub(r"\s*<link\b(?=[^>]*\brel\s*=\s*['\"]?stylesheet)(?=[^>]*\bhref\s*=\s*['\"](?!https?://)[^'\"]+\.css(?:\?[^'\"]*)?['\"])[^>]*>", "", html, flags=re.I)
    return re.sub(r"\s*<script\b(?=[^>]*\bsrc\s*=\s*['\"](?!https?://)[^'\"]+\.js(?:\?[^'\"]*)?['\"])[^>]*>\s*</script>", "", html, flags=re.I)


def _verified_contact_data(brief: MasterBrief, extraction: ExtractionSnapshot) -> dict[str, str]:
    """Merge only structured, source-derived contacts into the generation context."""
    result: dict[str, str] = {}
    for key, value in (brief.contactInfo or {}).items():
        if value and str(value).strip():
            result[key] = str(value).strip()
    contact_model = extraction.contactInfo
    extracted = (
        contact_model.model_dump(exclude_none=True)
        if hasattr(contact_model, "model_dump")
        else dict(contact_model or {})
    )
    aliases = {"hours": "officeHours", "contactUrl": "contactPageUrl"}
    for key, value in extracted.items():
        if key in {"sourceUrl", "confidence"} or not value:
            continue
        result.setdefault(aliases.get(key, key), str(value).strip())
    return result


def _enforce_footer_year(html: str, *, extraction: ExtractionSnapshot | None = None, company_name: str | None = None) -> str:
    """Normalize copyright years and add a current-year footer when absent."""
    year = str(datetime.now(timezone.utc).year)
    normalized = re.sub(r"((?:©|&copy;|copyright)[^<]{0,80}?)(?:20\d{2})", lambda match: match.group(1) + year, html, flags=re.I)
    footer_match = re.search(r"<footer\b[^>]*>(.*?)</footer>", normalized, re.I | re.S)
    if footer_match and not re.search(r"(?:©|&copy;|copyright)\s*20\d{2}", footer_match.group(1), re.I):
        label = company_name or (extraction.summary.companyName if extraction else None) or "Company"
        footer = footer_match.group(1).rstrip() + f' <span class="site-copyright">© {re.sub(r"[^A-Za-z0-9 &.-]", "", label)} {year}</span>'
        normalized = normalized[:footer_match.start(1)] + footer + normalized[footer_match.end(1):]
    return normalized


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
