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
from app.core.visual_adapter import build_visual_adapter
from app.schemas.brief import MasterBrief
from app.schemas.extraction import ExtractionSnapshot

logger = logging.getLogger(__name__)


class StaticGenerationError(ValueError):
    """Safe, structured failure raised before a static site is published."""

    def __init__(
        self,
        message: str,
        *,
        variant_type: str,
        stage: str,
        code: str,
    ) -> None:
        super().__init__(message)
        self.variant_type = variant_type
        self.stage = stage
        self.code = code


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

    # One prompt produces the page, stylesheet, and behavior as one design
    # system. Splitting these into independent requests loses the brief's art
    # direction and leads to unrelated, template-like assets.
    prompt = _build_static_html_prompt(master_brief, extraction, variant_type)
    adapter = build_visual_adapter(extraction, master_brief)
    from app.core.variant_strategy import get_variant_strategies
    art_direction_plan = get_variant_strategies(adapter=adapter)[variant_type].get("artDirectionPlan", {})
    logger.info(f"Generating static HTML for variant {variant_type} (site {site_id})")
    try:
        response = await llm.generate_text(
            prompt=prompt,
            temperature=0.7,
            max_tokens=32_768,
        )
        try:
            html_content, css_content, js_content = _parse_llm_response(response)
        except ValueError:
            # A retry must preserve the one-pass creative concept. Never
            # degrade to independent HTML/CSS/JS prompts after truncation.
            retry_prompt = (
                prompt
                + "\n\nYour previous response was truncated or malformed. Return the "
                "complete artifact now: exactly three CLOSED code blocks, in this order: "
                "```html, ```css, ```javascript. Include no commentary and do not omit "
                "or abbreviate any block."
            )
            logger.warning("Incomplete single-pass response for %s; retrying once", variant_type)
            response = await llm.generate_text(
                prompt=retry_prompt,
                temperature=0.7,
                max_tokens=32_768,
            )
            try:
                html_content, css_content, js_content = _parse_llm_response(response)
            except ValueError as retry_error:
                raise StaticGenerationError(
                    f"{variant_type} generation returned incomplete artifacts",
                    variant_type=variant_type,
                    stage="parse",
                    code="incomplete_artifact_response",
                ) from retry_error
    except StaticGenerationError:
        raise
    except Exception as exc:
        # Provider/model failures must fail the generation, never publish a
        # generic substitute website.
        logger.exception("Single-pass artifact generation failed for %s", variant_type)
        raise StaticGenerationError(
            f"{variant_type} generation failed before publication",
            variant_type=variant_type,
            stage="html",
            code="asset_generation_failed",
        ) from exc

    logger.info(
        f"[DEBUG] Single-pass assets received for {variant_type}: "
        f"html_len={len(html_content)}, css_len={len(css_content)}, js_len={len(js_content)}"
    )

    html_content = _enforce_footer_year(html_content, extraction=extraction, company_name=extraction.summary.companyName)
    try:
        _validate_generated_document(html_content, css_content, js_content, master_brief, extraction)
    except ValueError as exc:
        # Models occasionally leak a comment such as "placeholder" or use an
        # insecure source URL. Give the same coherent artifact one corrective
        # pass before rejecting the variant.
        logger.warning("Correcting invalid generated document for %s: %s", variant_type, exc)
        try:
            response = await llm.generate_text(
                prompt=_build_static_html_correction_prompt(
                    variant_type, html_content, css_content, js_content, str(exc), art_direction_plan,
                    _approved_render_asset_urls(master_brief),
                ),
                temperature=0.2,
                max_tokens=32_768,
            )
            html_content, css_content, js_content = _parse_llm_response(response)
            html_content = _enforce_footer_year(html_content, extraction=extraction, company_name=extraction.summary.companyName)
            _validate_generated_document(html_content, css_content, js_content, master_brief, extraction)
        except Exception as correction_error:
            logger.error("Rejecting invalid generated document for %s: %s", variant_type, correction_error)
            raise StaticGenerationError(
                f"{variant_type} generated invalid document: {correction_error}",
                variant_type=variant_type,
                stage="validation",
                code="document_validation_failed",
            ) from correction_error
    if not _javascript_is_valid(js_content):
        try:
            js_content = await _repair_javascript(llm, html_content, js_content, variant_type)
            _validate_generated_document(html_content, css_content, js_content, master_brief, extraction)
            if not _javascript_is_valid(js_content):
                raise ValueError("Generated JavaScript remains invalid after repair")
        except Exception as exc:
            logger.error("Rejecting invalid JavaScript for %s: %s", variant_type, exc)
            raise StaticGenerationError(
                f"{variant_type} generated invalid JavaScript: {exc}",
                variant_type=variant_type,
                stage="js",
                code="javascript_validation_failed",
            ) from exc

    html_content, css_content, js_content = _apply_static_safety_layer(
        html_content, css_content, js_content, master_brief, variant_type
    )

    # The model never owns delivery URLs. Remove any relative/generated asset
    # references before the backend deterministically injects the final URLs.
    html_content = _remove_generated_asset_references(html_content)

    # Upload CSS and JS to S3 only after every validation above has succeeded.
    settings = get_settings()
    logger.info(
        f"[DEBUG] S3 config: bucket={settings.asset_s3_bucket}, "
        f"prefix={settings.asset_s3_prefix}, region={settings.asset_s3_region}"
    )
    try:
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
    except Exception as exc:
        logger.exception("Static asset upload failed for %s", variant_type)
        raise StaticGenerationError(
            f"{variant_type} static asset upload failed",
            variant_type=variant_type,
            stage="upload",
            code="asset_upload_failed",
        ) from exc
    if settings.asset_s3_bucket and (not css_url or not js_url):
        raise StaticGenerationError(
            f"{variant_type} static asset upload did not return both public URLs",
            variant_type=variant_type,
            stage="upload",
            code="asset_upload_incomplete",
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
    company_name = extraction.summary.companyName or "Local Service Company"
    company = escape(company_name)
    contact = extraction.contactInfo
    office = escape(contact.officePhone or contact.emergencyPhone or "")
    emergency = escape(contact.emergencyPhone or contact.officePhone or "")
    hours = escape(contact.hours or "")
    approved_images = list(getattr(brief.brandAssets, "imageUrls", None) or [])
    approved_images.extend(
        item.get("url") for item in list(getattr(brief.brandAssets, "imageInventory", None) or [])
        if isinstance(item, dict) and item.get("url")
    )
    images = list(dict.fromkeys(_secure_asset_url(url) for url in approved_images if _secure_asset_url(url)))[:6]
    hero_image = escape(images[0] if images else "")
    logo_url = _approved_logo_url(brief) or ""
    cta_text = brief.ctaStrategy or "Contact us today"
    if re.search(r"xxx|placeholder|example\\.com", cta_text, re.IGNORECASE):
        cta_text = "Request a free estimate"
    mode = {"html_v1": ("Editorial Clarity", "#f4efe6", "#0d1b2a"), "html_v2": ("Confident Momentum", "#111827", "#c8860a"), "html_v3": ("Distinctive Warmth", "#eef7f2", "#4a6741")}.get(variant_type, ("Trusted Service", "#f4efe6", "#0d1b2a"))
    sections = list(brief.sections or [])[:6]
    section_html = "".join(
        f'<article><p class="eyebrow">{escape(s.purpose)}</p><h2>{escape(s.headline)}</h2><p>{escape(s.contentSummary)}</p></article>'
        for s in sections
    ) or f'<article><h2>How {company} helps</h2><p>{escape(brief.valueProposition or brief.businessGoal or f"Dependable service from {company}.")}</p></article>'
    gallery = "".join(f'<img src="{escape(url)}" alt="{company} field work">' for url in images[1:])
    logo = f'<img class="logo" src="{escape(logo_url)}" alt="{company} logo">' if logo_url else ''
    headline = escape(brief.headline or brief.valueProposition or f"Trusted service from {company_name}")
    subheadline = escape(brief.subheadline or brief.businessGoal or f"A clear, dependable experience from {company_name}.")
    primary_href = f"tel:{office}" if office else "#contact"
    contact_heading = escape(brief.ctaStrategy or f"Start a conversation with {company_name}")
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{company} - {mode[0]}</title><style>:root{{--bg:{mode[1]};--ink:{mode[2]};--accent:#c8860a}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:28px}}header{{min-height:72vh;display:grid;align-content:center;gap:24px;background:linear-gradient(90deg,var(--bg) 35%,transparent),url('{hero_image}') center/cover;border-radius:24px;padding:clamp(28px,8vw,110px)}}.logo{{max-width:150px;max-height:70px;object-fit:contain;object-position:left}}h1{{font-size:clamp(3rem,9vw,8rem);line-height:.9;max-width:850px;margin:0}}h2{{font-size:clamp(1.8rem,4vw,3.5rem);line-height:1.05}}.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:.75rem;font-weight:700;color:var(--accent)}}.cta{{display:inline-block;background:var(--accent);color:#fff;padding:14px 22px;border-radius:999px;text-decoration:none;font-weight:700;width:max-content}}section{{padding:90px 0}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}article{{padding:26px;border:1px solid color-mix(in srgb,var(--ink) 18%,transparent);border-radius:18px}}.gallery{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.gallery img{{width:100%;height:220px;object-fit:cover;border-radius:14px}}footer{{border-top:1px solid color-mix(in srgb,var(--ink) 20%,transparent);padding:30px 0}}@media(max-width:700px){{main{{padding:16px}}header{{min-height:78vh;padding:28px 20px}}.grid,.gallery{{grid-template-columns:1fr}}.gallery img{{height:180px}}}}</style></head><body><main><header>{logo}<p class="eyebrow">{escape(mode[0])}</p><h1>{headline}</h1><p>{subheadline}</p><a class="cta" href="{primary_href}">{escape(cta_text)}</a></header><section><p class="eyebrow">What we do</p><div class="grid">{section_html}</div></section><section><p class="eyebrow">Highlights</p><div class="gallery">{gallery}</div></section><section id="contact"><p class="eyebrow">Contact</p><h2>{contact_heading}</h2><p>{('Office: <a href="tel:' + office + '">' + office + '</a><br>') if office else ''}{('Emergency: <a href="tel:' + emergency + '">' + emergency + '</a><br>') if emergency else ''}{hours}</p><a class="cta" href="{escape(contact.contactUrl or '#contact')}">Contact the team</a></section><footer><span class="site-copyright">© {company} {datetime.now(timezone.utc).year}</span></footer></main><script>window.__LENMANAG_RUNTIME__={{initialized:true,animationSetupComplete:true,errors:[],jsLoaded:true}};window.__LENMANAG_STATIC_READY__=true;</script></body></html>'''
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
    adapter = build_visual_adapter(extraction, brief)
    from app.core.variant_strategy import get_variant_strategies
    strategy = get_variant_strategies(adapter=adapter)[variant_type]
    plan = strategy.get("artDirectionPlan") or {}
    # Build sections summary
    sections_summary = "\n".join(
        f"  - {s.purpose}: {s.headline}\n    Purpose: {s.contentSummary}\n    Approved points: {', '.join(s.contentPoints)}\n    Approach: {s.suggestedApproach}"
        for s in brief.sections
    ) or "  - No approved sections; create visual interest without inventing facts."

    # Get brand info
    logo_url = _secure_asset_url(brief.brandAssets.logoUrl) or "None"
    primary_color = brief.brandAssets.primaryColor or "#000000"
    secondary_color = brief.brandAssets.secondaryColor or "#666666"
    font_family = _safe_font_family(brief.brandAssets.fontFamily) or "Roboto, Nunito, Inter, system-ui, sans-serif"
    font_url = _secure_asset_url(brief.brandAssets.fontUrl) or "None"
    year = datetime.now(timezone.utc).year
    contacts = _verified_contact_data(brief, extraction)
    image_inventory = [item for item in brief.brandAssets.imageInventory if item.get("url")][:12]
    if not image_inventory:
        image_inventory = [{"category": "image", "url": url} for url in (brief.brandAssets.imageUrls or []) if url][:12]
    asset_inventory = "\n".join(f"- {item.get('category', 'image')}: {_secure_asset_url(item.get('url')) or ''} | alt={item.get('altText') or ''} | dimensions={item.get('width') or '?'}x{item.get('height') or '?'} | confidence={item.get('confidence') or 0}" for item in image_inventory if _secure_asset_url(item.get('url'))) or "- No approved photography is available; omit photography and use art direction"

    approved_testimonials = _approved_testimonial_quotes(extraction)
    testimonials_context = "\n".join(f'- "{quote}"' for quote in approved_testimonials) or "- None approved. Do not render testimonials, reviews, star ratings, or customer quotes."

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
- Scroll Behavior: {brief.creativeDirection.scrollBehavior}
- Color Mood: {brief.creativeDirection.colorMood}
- Typography: {brief.creativeDirection.typographyPersonality}
- Micro-interactions: {', '.join(brief.creativeDirection.microInteractions) or 'None specified'}
- Inspiration Keywords: {', '.join(brief.creativeDirection.inspirationKeywords) or 'None specified'}
- Avoid Patterns: {', '.join(brief.creativeDirection.avoidPatterns) or 'None specified'}

CONTENT BLUEPRINT:
- Hero Headline: {brief.headline}
- Hero Subheadline: {brief.subheadline}
- Sections:
{sections_summary}
- CTA Strategy: {brief.ctaStrategy}

BRAND ASSETS:
- Company Name: {company_name}
- Logo URL: {_secure_asset_url(logo_url) or logo_url}
- Primary Color: {primary_color}
- Secondary Color: {secondary_color}
- Font Family: {font_family}
- Font File URL: {font_url}
    - Logo variants: {', '.join(_secure_asset_url(url) for url in brief.brandAssets.logoVariants if _secure_asset_url(url)) or 'None'}
- Approved image inventory (use these URLs, never random stock):
{asset_inventory}
- Approved testimonials (use verbatim or omit the entire proof/testimonial section):
{testimonials_context}
- Verified contact data: {contacts or 'None; omit rather than invent'}
- Current server year for footer copyright: {year}

VARIANT TYPE: {variant_type}

INDUSTRY AND AUDIENCE VISUAL ADAPTER:
- Industry: {adapter['industry']} / {adapter['subcategory']}
- Audience and buying context: {adapter['audience']}
- Trust signals: {', '.join(adapter['trust'])}
- Appropriate imagery: {', '.join(adapter['imagery'])}
- Visual metaphors: {', '.join(adapter['metaphors'])}
- Interaction patterns: {', '.join(adapter['interaction'])}
- Motion language: {adapter['motion']}
- Typography personality: {adapter['type']}
- Color behavior: {adapter['color']}
- Patterns to avoid: {', '.join(adapter['avoid'])}
- Conceptual imagery useful: {adapter['conceptual']}

ART-DIRECTION IMPLEMENTATION PLAN (implement this plan, do not invent a competing design):
{plan}

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
    - REQUIRED HEADER LOGO URL: {logo_url}
    - If this URL is not None, the <header> MUST contain an <img> whose src equals this exact URL. Do not omit, rewrite, substitute, or use a different logo variant. If it is None, no logo is required.
   - Map approved assets to header, hero, service/about, and footer before writing markup. If an approved logo exists, the header MUST contain it. If approved photography exists, use at least one <img> unless this specific concept is explicitly typography-only.
    - Use only the verified contact data above. Never invent phone numbers, emails, addresses, metrics, or placeholder contacts. Use the current server year in the copyright footer.
    - Every image, logo, font, and CSS background asset must use one of the cached URLs listed above, a data: URL, or no asset at all. Never request, copy, upgrade, or mention a URL from the original website.
   - NO inline styles or scripts
   - Use approved extracted client images first. If none are suitable, prefer typographic, geometric, textured, or diagrammatic art direction. Use external imagery only when genuinely necessary and contextually relevant; never use random stock photography.
   - If a font file URL is provided, load it with @font-face; never use placeholder family names such as "Preloaded Font" as literal CSS.
   - Never use Arial, Comic Sans, or other basic Windows font families. Prefer an approved font, or use Roboto, Nunito, Inter, system-ui, sans-serif, or a comparable web-safe alternative.

3. CSS Requirements:
   - Use CSS custom properties for colors/spacing
   - Responsive design (mobile-first with media queries)
    - Smooth animations matching motion level, with a visible signature transition or hover treatment and a prefers-reduced-motion fallback
    - Include min-width: 0 on grid/flex children, max-width: 100% on media, overflow-wrap: anywhere on long copy, and responsive gaps. No text may escape a card, button, or section.
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
   - Produce an Awwwards-quality experience, not a conventional business template.
   - Carry one coherent visual concept through the whole page. Make the design concept,
     hero treatment, layout strategy, palette behavior, and signature technique visibly
     consequential rather than decorative labels.
   - Create strong typography, intentional composition, varied section layouts, depth,
     and excellent spacing. Use the approved signature technique prominently.
   - Implement purposeful motion and the specified micro-interactions in vanilla
     JavaScript/CSS; its motion language must match the stated motion level and scroll behavior.
   - Do not repeat rows, cards, or section treatments. Avoid spreadsheet-like layouts,
     generic service grids, excessive empty space, simple document styling, and every
     pattern listed in Avoid Patterns.
   - If approved photography is unavailable, create intentional art direction with
     typography, SVG, gradients, textures, canvas, geometry, and layered composition;
     never leave an empty or generic page.
    - Keep factual accuracy: use only approved client assets and verified facts. Never
     invent testimonials, reviews, phone numbers, emails, addresses, metrics, awards,
     or claims. Include a testimonial only when its exact quote appears in the approved
     testimonial list above; otherwise omit testimonials entirely.
   - Hard copy rules: never use an em dash (—) anywhere. Use a hyphen or rewrite the sentence.
    - Never output placeholder language, including lorem ipsum, example.com, TODO, XXX, "your email", "contact us for details", "coming soon", or "image placeholder". If source data is missing, omit that element.
    - Keep copy compact: hero headline <= 12 words, paragraph copy <= 45 words, card titles <= 8 words, card copy <= 24 words. Split or omit content rather than overflowing a component.
   - Use only browser-native HTML, CSS, SVG, canvas, and vanilla JavaScript. Do not
     import, claim, or rely on Three.js, GSAP, Lenis, or any other unprovided library.

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


def _validate_generated_document(
    html: str,
    css: str,
    js: str,
    brief: MasterBrief | None = None,
    extraction: ExtractionSnapshot | None = None,
) -> None:
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
    prohibited = (r"\b(?:xxx|xxxx|000-0000|555[- )]?\d{3,4}|lorem ipsum|example\.com|your@email\.com|todo|coming soon|contact us for details|image placeholder)\b")
    if re.search(prohibited, "\n".join((html, css, js)), re.I):
        raise ValueError("Generated output contains prohibited placeholder content")
    if "—" in "\n".join((html, css, js)):
        raise ValueError("Generated output contains an em dash; use a hyphen instead")
    if re.search(r"\b(?:arial|comic\s+sans(?:\s+ms)?)\b", "\n".join((html, css, js)), re.I):
        raise ValueError("Generated output uses a prohibited basic Windows font")
    if re.search(r"\b(?:eval|Function)\s*\(", js) or re.search(r"\b(?:setTimeout|setInterval)\s*\(\s*['\"]", js):
        raise ValueError("Generated JavaScript uses prohibited dynamic code evaluation")
    if re.search(r"(?:src|href)\s*=\s*['\"]http://|url\(\s*['\"]?http://", "\n".join((html, css)), re.I):
        raise ValueError("Generated document contains an insecure HTTP resource URL")
    if extraction is not None and _has_testimonial_markup_without_approved_quote(html, extraction):
        raise ValueError("Generated output contains an unapproved testimonial or review")
    if brief:
        current_year = str(datetime.now(timezone.utc).year)
        if re.search(r"(?:copyright|©|&copy;)[^<]{0,80}\b20\d{2}\b", html, re.I) and current_year not in html:
            raise ValueError("Generated footer uses a stale year")
        required_logo_url = _approved_logo_url(brief)
        if required_logo_url and not _header_contains_exact_logo(html, required_logo_url):
            raise ValueError("Generated HTML omitted the approved header logo")
    if _has_unapproved_render_asset(html, css, brief):
        raise ValueError("Generated document contains an uncached or unapproved asset URL")
    if brief:
        approved_images = [
            _secure_asset_url(url)
            for url in list(getattr(brief.brandAssets, "imageUrls", None) or [])
        ]
        approved_images.extend(
            _secure_asset_url(item.get("url"))
            for item in list(getattr(brief.brandAssets, "imageInventory", None) or [])
            if isinstance(item, dict)
        )
        approved_images = [url for url in approved_images if url]
        if approved_images and not any(url in html for url in approved_images):
            raise ValueError("Generated HTML omitted approved photography")


def _approved_logo_url(brief: MasterBrief) -> str | None:
    assets = getattr(brief, "brandAssets", None)
    if assets is None:
        return None
    for value in (
        getattr(assets, "logoUrl", None),
        getattr(assets, "logoLightUrl", None),
        getattr(assets, "logoDarkUrl", None),
        *(getattr(assets, "logoVariants", None) or []),
    ):
        if isinstance(value, str) and value.strip():
            return _secure_asset_url(value) or value.strip()
    return None


def _secure_asset_url(value: object) -> str | None:
    """Normalize public asset URLs so hosted previews do not trigger mixed content."""
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.lower().startswith("http://"):
        return "https://" + value[7:]
    return value if value.lower().startswith(("https://", "data:", "/api/internal/assets/")) else None


def _approved_render_asset_urls(brief: MasterBrief | None) -> set[str]:
    if brief is None:
        return set()
    assets = getattr(brief, "brandAssets", None)
    if assets is None:
        return set()
    values = [
        getattr(assets, "logoUrl", None), getattr(assets, "logoLightUrl", None),
        getattr(assets, "logoDarkUrl", None), getattr(assets, "fontUrl", None),
        *(getattr(assets, "logoVariants", None) or []),
        *(getattr(assets, "imageUrls", None) or []),
        *[
            item.get("url") for item in (getattr(assets, "imageInventory", None) or [])
            if isinstance(item, dict)
        ],
    ]
    return {url for value in values if (url := _secure_asset_url(value))}


def _has_unapproved_render_asset(html: str, css: str, brief: MasterBrief | None) -> bool:
    """Reject source-site assets while allowing normal navigation links."""
    if brief is None:
        return False
    approved = _approved_render_asset_urls(brief)
    asset_values: list[str] = []
    for match in re.finditer(r"<img\b[^>]*\bsrc\s*=\s*(['\"])(.*?)\1", html, re.I | re.S):
        asset_values.append(match.group(2).strip())
    for match in re.finditer(r"\b(?:src|poster)\s*=\s*(['\"])(.*?)\1", html, re.I | re.S):
        asset_values.append(match.group(2).strip())
    for match in re.finditer(r"<link\b[^>]*\bhref\s*=\s*(['\"])(.*?)\1", html, re.I | re.S):
        asset_values.append(match.group(2).strip())
    asset_values.extend(match.group(2).strip() for match in re.finditer(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css, re.I | re.S))
    return any(
        value.startswith(("http://", "https://", "/api/internal/assets/"))
        and not value.startswith("data:")
        and value not in approved
        for value in asset_values
    )


def _safe_font_family(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if re.search(r"\b(?:arial|comic\s+sans(?:\s+ms)?)\b", value, re.I):
        return None
    return value.strip()


def _upgrade_insecure_resource_urls(html: str) -> str:
    """Upgrade generated resource attributes to HTTPS."""
    html = re.sub(
        r"(?P<prefix>\b(?:src|href)\s*=\s*['\"])http://",
        r"\g<prefix>https://",
        html,
        flags=re.I,
    )
    return re.sub(r"(url\(\s*['\"]?)http://", r"\1https://", html, flags=re.I)


def _approved_testimonial_quotes(extraction: ExtractionSnapshot) -> list[str]:
    quotes: list[str] = []
    analysis = getattr(extraction, "analysis", None)
    items = list(getattr(analysis, "testimonials", None) or []) + list(getattr(extraction, "extractedTestimonials", None) or [])
    for item in items:
        quote = getattr(item, "quote", None) if not isinstance(item, dict) else item.get("quote")
        if isinstance(quote, str) and quote.strip() and quote.strip() not in quotes:
            quotes.append(quote.strip())
    return quotes[:12]


def _has_testimonial_markup_without_approved_quote(html: str, extraction: ExtractionSnapshot) -> bool:
    lowered = html.lower()
    markers = ("testimonial", "review", "customer quote", "what clients say", "said by")
    if not any(marker in lowered for marker in markers):
        return False
    return not any(quote.lower() in lowered for quote in _approved_testimonial_quotes(extraction))


def _build_static_html_correction_prompt(
    variant_type: str, html: str, css: str, js: str, error: str,
    plan: dict[str, Any] | None = None,
    approved_asset_urls: set[str] | None = None,
) -> str:
    return f"""Repair the generated static site artifact for {variant_type}. Return ONLY three closed code blocks in this order: html, css, javascript. Preserve the design and all source-backed content, but fix this validation error: {error}

Preserve and implement the original art-direction plan; do not replace it with a generic fallback:
{plan or 'Preserve the existing concept, composition, imagery, and interaction intent.'}

Hard rules:
- Never use an em dash. Use a hyphen.
- Never use placeholder content or invented testimonials, reviews, claims, metrics, contacts, or images.
    - Use only these approved cached asset URLs, data: assets, or no asset at all: {', '.join(sorted(approved_asset_urls or set())) or 'none'}.
    - Never use an original-site URL, even if it can be upgraded to HTTPS. Remove any uncached image or logo.
- Never use Arial or Comic Sans.
- JavaScript must be vanilla and must not use eval(), new Function(), or string-based timers.
- Keep the required runtime call: window.__LENMANAG_RUNTIME__.markInitialized().

```html
{html}
```
```css
{css}
```
```javascript
    {js}
    ```"""


def _apply_static_safety_layer(
    html: str, css: str, js: str, brief: MasterBrief, variant_type: str
) -> tuple[str, str, str]:
    """Guarantee readable layout and progressive enhancement for every variant."""
    required_logo = _approved_logo_url(brief)
    light_logo = _secure_asset_url(getattr(brief.brandAssets, "logoLightUrl", None))
    if required_logo and light_logo and required_logo == light_logo:
        header_match = re.search(r"<header\b[^>]*>(.*?)</header\s*>", html, re.I | re.S)
        if header_match:
            header = re.sub(
                r"(<img\b[^>]*\bsrc\s*=\s*['\"]" + re.escape(required_logo) + r"['\"][^>]*)",
                r'\1 class="lq-logo-dark-on-light"',
                header_match.group(1), count=1, flags=re.I | re.S,
            )
            html = html[:header_match.start(1)] + header + html[header_match.end(1):]

    html = re.sub(
        r"<((?:section|article|figure|footer)\b(?![^>]*\bdata-lq-reveal\b)(?![^>]*\bclass=['\"][^'\"]*(?:hero|header)[^'\"]*['\"])[^>]*)>",
        r'<\1 data-lq-reveal>', html, flags=re.I,
    )
    css += """

/* LenQuant reliability layer: readable by default, enhanced when JS is ready. */
*, *::before, *::after { box-sizing: border-box; }
html { overflow-x: hidden; }
body, main, header, section, article, footer, div, li { min-width: 0; }
body { overflow-wrap: anywhere; }
img, svg, video, canvas { display: block; max-width: 100%; height: auto; }
h1, h2, h3, h4, p, a, button, li { overflow-wrap: anywhere; }
[data-lq-reveal] { opacity: 1; transform: none; }
.lq-motion-ready [data-lq-reveal] { opacity: 0; transform: translateY(22px); transition: opacity .7s ease, transform .7s cubic-bezier(.2,.7,.2,1); }
.lq-motion-ready [data-lq-reveal].lq-revealed { opacity: 1; transform: none; }
.lq-logo-dark-on-light { filter: brightness(0) saturate(100%); }
[data-lq-float] { animation: lq-float 8s ease-in-out infinite; }
@keyframes lq-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
  .lq-motion-ready [data-lq-reveal] { opacity: 1; transform: none; }
}
@media (max-width: 720px) {
  [class*="grid"], [class*="columns"] { grid-template-columns: minmax(0, 1fr) !important; }
}
"""
    js += """

// LenQuant progressive motion layer. Content stays visible if this script fails.
(function () {
  function setupLenQuantMotion() {
    var root = document.documentElement;
    var items = Array.prototype.slice.call(document.querySelectorAll('[data-lq-reveal]'));
    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduced || !('IntersectionObserver' in window)) {
      items.forEach(function (item) { item.classList.add('lq-revealed'); });
      if (window.__LENMANAG_RUNTIME__ && window.__LENMANAG_RUNTIME__.markInitialized) window.__LENMANAG_RUNTIME__.markInitialized();
      return;
    }
    root.classList.add('lq-motion-ready');
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) { entry.target.classList.add('lq-revealed'); observer.unobserve(entry.target); }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (item) { observer.observe(item); });
    var floatTarget = document.querySelector('.hero-visual, [data-hero-visual]');
    if (floatTarget) floatTarget.setAttribute('data-lq-float', 'true');
    if (window.__LENMANAG_RUNTIME__ && window.__LENMANAG_RUNTIME__.markInitialized) window.__LENMANAG_RUNTIME__.markInitialized();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupLenQuantMotion);
  else setupLenQuantMotion();
}());
"""
    return html, css, js


def _header_contains_exact_logo(html: str, required_url: str) -> bool:
    """Check the strict logo contract without accepting a logo elsewhere."""
    header_match = re.search(r"<header\b[^>]*>(.*?)</header\s*>", html, re.I | re.S)
    if not header_match:
        return False
    header = header_match.group(1)
    for image in re.finditer(r"<img\b[^>]*>", header, re.I | re.S):
        src_match = re.search(r"\bsrc\s*=\s*(['\"])(.*?)\1", image.group(0), re.I | re.S)
        if src_match and src_match.group(2).strip() == required_url:
            return True
    return False


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
