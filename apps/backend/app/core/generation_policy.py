"""Source evidence rules shared by briefs, generation, and refinement."""

from __future__ import annotations

import re
from html import escape

from bs4 import BeautifulSoup

from app.schemas.extraction import BrandAssetCue, ExtractionSnapshot

FOOTER_YEAR = "2026"
FOOTER_YEAR_POLICY = (
    "FOOTER YEAR RULE: If the footer displays a copyright/legal year, use the literal year 2026. "
    "Never copy an old copyright year from the source website or use a dynamic current year. "
    "Do not invent a year when the footer has none. Preserve genuine founding dates."
)


def _footer_year_text(text: str) -> str:
    def replace(match: re.Match) -> str:
        prefix = text[max(0, match.start() - 40):match.start()]
        if re.search(r"\b(?:since|founded|established|est\.)\s*$", prefix, re.I):
            return match.group()
        return FOOTER_YEAR

    return re.sub(r"\b(?:19|20)\d{2}(?:\s*[-–—]\s*(?:19|20)\d{2})?\b", replace, text)


def enforce_html_footer_year(html: str) -> str:
    """Normalize visible footer years without changing assets or historical claims."""
    soup = BeautifulSoup(html, "html.parser")
    for footer in soup.select('footer, [role="contentinfo"]'):
        for node in list(footer.find_all(string=True)):
            if node.parent.name in {"script", "style"}:
                continue
            original = str(node)
            updated = _footer_year_text(original)
            if updated != original:
                node.replace_with(updated)
    return str(soup)


def enforce_source_footer_year(source: str) -> str:
    """Preserve JSX markup while fixing footer literals and inline year expressions."""
    def footer(match: re.Match) -> str:
        block = match.group()
        block = re.sub(r"new Date\(\)\.getFullYear\(\)", FOOTER_YEAR, block)
        return re.sub(r"(?<=>)([^<]+)(?=<)", lambda text: _footer_year_text(text.group()), block)

    return re.sub(r"<footer\b[^>]*>.*?</footer\s*>", footer, source, flags=re.I | re.S)


def normalize_color(value: str) -> str | None:
    value = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        return "#" + "".join(char * 2 for char in value[1:])
    if re.fullmatch(r"#[0-9a-f]{6}", value):
        return value
    match = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", value)
    if match and all(int(part) <= 255 for part in match.groups()):
        return "#" + "".join(f"{int(part):02x}" for part in match.groups())
    return None


def primary_brand_cue(extraction: ExtractionSnapshot | None) -> BrandAssetCue | None:
    if extraction is None:
        return None
    cues = [cue for cue in extraction.brandAssetCues if cue.assetType == "color" and normalize_color(cue.value)]

    def rank(cue: BrandAssetCue) -> tuple[int, int, int]:
        label = cue.label.lower()
        explicit = bool(re.search(r"primary|cta|button", label))
        color = normalize_color(cue.value) or "#000000"
        channels = [int(color[index:index + 2], 16) for index in (1, 3, 5)]
        chromatic = max(channels) - min(channels) > 30
        return (3 if explicit else 2 if "brand" in label else int(chromatic), cue.confidence, max(channels) - min(channels))

    return max(cues, key=rank) if cues else None


def brand_color_policy(extraction: ExtractionSnapshot | None) -> str:
    cue = primary_brand_cue(extraction)
    if not cue:
        return "No source primary color was extracted. Choose a coherent palette and label the choice as inferred."
    color = normalize_color(cue.value)
    return (
        f"SOURCE BRAND COLOR RULE: The extracted principal brand color is {color} "
        f"(source: {cue.sourceUrl}). Preserve this exact color as the principal brand color "
        "in every design, including primary buttons, links, and brand accents. Set "
        f"--brand-primary: {color}; and use var(--brand-primary) for primary actions. "
        "Creative direction, industry styling, dark mode, and palette variants cannot replace it. "
        "Use complementary colors only as secondary accents. Choose contrasting text for accessibility."
    )


def stylesheet_color_cues(css: str, source_url: str) -> list[dict]:
    """Rank source CSS colors by named brand variables and action styling."""
    scores: dict[str, int] = {}
    declared_primary: dict[str, str] = {}
    primary_names = ("--brand-primary", "--brand-color", "--primary-color", "--color-primary", "--primary")
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # Split complete blocks and declarations rather than retrying an unanchored
    # regex at every byte of a large/truncated inline font or data URL.
    for block in css.split("}")[:-1]:
        if "{" not in block:
            continue
        selector, declarations = block.rsplit("{", 1)
        for declaration in declarations.split(";"):
            property_name, separator, raw_value = declaration.partition(":")
            property_name = property_name.strip()
            if not separator or not re.fullmatch(r"[\w-]+", property_name):
                continue
            value_match = re.match(r"\s*(#[0-9a-fA-F]{3,6}\b|rgb\([^)]*\))", raw_value)
            if not value_match:
                continue
            value = value_match.group(1)
            color = normalize_color(value)
            if not color:
                continue
            if property_name.lower() in primary_names:
                declared_primary[property_name.lower()] = color
            channels = [int(color[index:index + 2], 16) for index in (1, 3, 5)]
            named_brand = property_name.startswith("--") and bool(re.search(r"brand|primary", property_name, re.I))
            if max(channels) - min(channels) <= 30 and not named_brand:
                continue
            if not (property_name.startswith("--") or property_name in {"color", "background", "background-color", "border-color"}):
                continue
            action = bool(re.search(r"button|btn|cta|header|nav|logo|brand|\ba(?=[:.\s,]|$)", selector, re.I))
            scores[color] = scores.get(color, 0) + (30 if named_brand else 5 if action else 1)
    ranked = sorted(scores, key=lambda color: scores[color], reverse=True)
    explicit = next((declared_primary[name] for name in primary_names if name in declared_primary), None)
    if explicit:
        ranked = [explicit, *[color for color in ranked if color != explicit]]
    return [{"assetType": "color", "label": "Primary brand color" if index == 0 else "Source accent color",
             "value": color, "sourceUrl": source_url, "confidence": (99 if color == explicit else min(95, 75 + scores[color])) if index == 0 else 70,
             "note": "Ranked from source stylesheet brand variables and navigation/action color usage."}
            for index, color in enumerate(ranked[:3])]


def rendered_brand_cues(data: dict, source_url: str) -> list[dict]:
    """Prefer the live theme's primary variable or visible action color to framework CSS."""
    for value in data.get("brandVariables", []):
        color = normalize_color(value)
        if color:
            return [{"assetType": "color", "label": "Primary brand color from rendered theme variable",
                     "value": color, "sourceUrl": source_url, "confidence": 100,
                     "note": "Resolved from the active source theme, after CSS overrides."}]
    colors = []
    neutral_actions = []
    for value in data.get("actionColors", []):
        color = normalize_color(value)
        if color:
            channels = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
            if max(channels) - min(channels) > 30:
                colors.append(color)
            elif max(channels) < 160:
                neutral_actions.append(color)
    if not colors:
        # Some brands use outlined/transparent buttons; colored service headings
        # are stronger evidence than colors from unrelated gallery plugins.
        for value in data.get("headingColors", []):
            color = normalize_color(value)
            if color:
                channels = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
                if max(channels) - min(channels) > 30:
                    colors.append(color)
        if not colors:
            if neutral_actions:
                color = max(dict.fromkeys(neutral_actions), key=neutral_actions.count)
                return [{"assetType": "color", "label": "Primary brand color from rendered monochrome actions",
                         "value": color, "sourceUrl": source_url, "confidence": 96,
                         "note": "Source uses dark neutral conversion buttons with no colored heading or action accents."}]
            dark_headings = []
            for value in data.get("headingColors", []):
                color = normalize_color(value)
                if color and max(int(color[i:i + 2], 16) for i in (1, 3, 5)) < 160:
                    dark_headings.append(color)
            if dark_headings:
                color = max(dict.fromkeys(dark_headings), key=dark_headings.count)
                return [{"assetType": "color", "label": "Primary brand color from monochrome source headings",
                         "value": color, "sourceUrl": source_url, "confidence": 90,
                         "note": "Monochrome source typography fallback when no colored brand styling is available."}]
            return []
        color = max(dict.fromkeys(colors), key=colors.count)
        return [{"assetType": "color", "label": "Primary brand color from rendered source headings",
                 "value": color, "sourceUrl": source_url, "confidence": 96,
                 "note": "Most frequent chromatic heading color when source conversion buttons are transparent."}]
    color = max(dict.fromkeys(colors), key=colors.count)
    return [{"assetType": "color", "label": "Primary brand color from rendered source actions",
             "value": color, "sourceUrl": source_url, "confidence": 98,
             "note": "Most frequent chromatic background of visible source conversion buttons; excludes framework defaults."}]


def is_testimonial_section(value: str) -> bool:
    return bool(re.search(
        r"testimonial|customer[\s_-]+(?:quote|review)|client[\s_-]+(?:quote|review)|\breviews\b|schema.org/Review|(?:quote|review)[\s_-]*(?:card|carousel|section|rating)|"
        r"endorsement|what\s+(?:our\s+)?(?:clients|customers|homeowners)\s+say",
        value, re.I,
    ))


def source_testimonials(extraction: ExtractionSnapshot | None):
    """Low-confidence proof text can be navigation or headings, not a review."""
    return [record for record in (extraction.extractedTestimonials if extraction else [])
            if record.quote.strip() and record.sourceUrl and record.confidence >= 70]


def apply_brief_policy(brief, extraction: ExtractionSnapshot):
    """Enforce evidence even when an AI brief suggests unsupported content."""
    brief = brief.model_copy(deep=True)
    cue = primary_brand_cue(extraction)
    if cue:
        brief.brandAssets.primaryColor = normalize_color(cue.value)
        policy = brand_color_policy(extraction)
        if policy not in brief.colorStrategy:
            brief.colorStrategy = policy + "\n" + brief.colorStrategy
    if not source_testimonials(extraction):
        brief.sections = [section for section in brief.sections if not is_testimonial_section(
            " ".join([section.purpose, section.headline, section.contentSummary, section.suggestedApproach, *section.contentPoints])
        )]
    return brief


def enforce_html_testimonials(html: str, extraction: ExtractionSnapshot | None) -> str:
    """Render quotes from extraction records; remove AI-written review regions."""
    soup = BeautifulSoup(html, "html.parser")
    for node in list(soup.find_all(True)):
        if node.parent is None:
            continue
        marker = " ".join([str(node.get("id", "")), " ".join(node.get("class", [])), str(node.get("itemtype", "")), str(node.get("aria-label", ""))])
        heading = node.get_text(" ", strip=True) if node.name in {"h2", "h3", "h4"} else ""
        direct_text = " ".join(str(text) for text in node.find_all(string=True, recursive=False)).strip() if node.name not in {"script", "style", "head", "title", "textarea"} else ""
        rating = re.search(r"google\s+reviews?|\b[1-5](?:\.\d)?\s*/\s*5\b|\b[1-5](?:\.\d)?[\s-]+stars?\b|\bstar[\s-]+reviews?\b|[★⭐]{3,}", direct_text, re.I)
        quote_context = " ".join([direct_text, marker, *[" ".join(parent.get("class", [])) for parent in node.parents if parent.attrs]])
        customer_quote = re.search(r'["“][^"”]{25,}["”]', direct_text) and re.search(r"homeowner|customer|client|ticker|testimonial|quote|trust|proof|review", quote_context, re.I)
        if is_testimonial_section(marker) or is_testimonial_section(heading) or node.name == "blockquote" or rating or customer_quote:
            region = node.find_parent("section") or node
            region.decompose()
    # Review schemas can invent ratings even without a visible review section.
    for node in list(soup.find_all("script", type="application/ld+json")):
        if re.search(r'"(?:Review|AggregateRating|review|aggregateRating)"', node.get_text()):
            node.decompose()
    records = source_testimonials(extraction)
    if records and soup.body:
        cards = []
        for record in records[:6]:
            attribution = ", ".join(part for part in [record.authorName, record.authorTitle, record.authorCompany] if part)
            cards.append(f'<figure><blockquote>{escape(record.quote)}</blockquote>' + (f'<figcaption>{escape(attribution)}</figcaption>' if attribution else "") + '</figure>')
        section = BeautifulSoup('<section id="source-testimonials" class="source-testimonials" aria-label="Customer testimonials"><h2>What our customers say</h2>' + "".join(cards) + '</section>', "html.parser")
        footer = soup.body.find("footer")
        if footer:
            footer.insert_before(section)
        else:
            soup.body.append(section)
    for link in list(soup.find_all("a", href=True)):
        if link["href"].startswith("#") and is_testimonial_section(link["href"]):
            if records:
                link["href"] = "#source-testimonials"
            else:
                link.decompose()
    return str(soup)


def static_safety_css(extraction: ExtractionSnapshot | None) -> str:
    cue = primary_brand_cue(extraction)
    color = normalize_color(cue.value) if cue else None
    brand = ""
    if color:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
        luminance = sum(channel * weight for channel, weight in zip(linear, [0.2126, 0.7152, 0.0722]))
        text_color = "#000000" if luminance > 0.179 else "#ffffff"
        brand = f""":root {{ --brand-primary: {color} !important; --primary-color: {color} !important; --color-primary: {color} !important; }}
[data-primary-cta], .btn-primary, .button-primary {{ background-color: var(--brand-primary) !important; color: {text_color} !important; }}
"""
    return brand + """
/* The hero is readable before JavaScript loads and if an enhancement fails. */
html, body { cursor: auto !important; }
a, button, [role="button"], input[type="submit"] { cursor: pointer !important; }
.custom-cursor, #custom-cursor, [data-custom-cursor] { display: none !important; }
h1, h1 *, [data-hero-headline], [data-hero-headline] *, .headline-word {
  opacity: 1 !important; visibility: visible !important; clip-path: none !important;
  transform: none !important; animation: none !important;
}
.source-testimonials { padding: clamp(2rem, 6vw, 5rem); }
.source-testimonials figure { margin: 1.5rem 0; padding: 1.5rem; border-left: 3px solid var(--brand-primary, currentColor); }
.source-testimonials blockquote { margin: 0 0 1rem; }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
  .reveal, .animate-on-scroll { opacity: 1 !important; clip-path: none !important; transform: none !important; }
}
"""


def validate_testimonial_source(source: str, extraction: ExtractionSnapshot | None) -> list[str]:
    """Reject unsupported review content in generated React code before compilation."""
    has_records = bool(source_testimonials(extraction))
    markers = re.search(r"<blockquote\b|\btestimonials?\b|\breviews\s*[=:]|(?:id|className)\s*=\s*[\"'][^\"']*review|AggregateRating|customer reviews|what (?:our )?(?:customers|clients|homeowners) say", source, re.I)
    if markers and not has_records:
        return ["Remove testimonials, customer reviews, quote cards, and review ratings: no source testimonials were extracted."]
    if markers and has_records:
        # Quote data must be copied exactly, rather than paraphrased into an invented review.
        for quote in re.findall(r"\bquote\s*:\s*([\"'`])(.+?)\1", source, re.S):
            value = quote[1].replace("\\'", "'").replace('\\"', '"')
            if not any(value == record.quote for record in source_testimonials(extraction)):
                return ["A testimonial quote does not match the extracted source evidence. Use exact source quotes only."]
    return []
