"""Shared capability-manifest construction for generated browser entries."""

from __future__ import annotations

import re
from typing import Any


# Keep this list in sync with apps/compiler/src/validate.ts.  The manifest is
# derived from the generated entry, but an import is still rejected unless it
# belongs to this explicit surface.
APPROVED_BROWSER_DEPENDENCIES = (
    "react",
    "react-dom",
    "react/jsx-runtime",
    "react/jsx-dev-runtime",
    "framer-motion",
    "gsap",
    "gsap/ScrollTrigger",
    "lenis",
    "embla-carousel-react",
    "lucide-react",
    "clsx",
    "tailwind-merge",
    "three",
    "@react-three/fiber",
    "@react-three/drei",
    "@radix-ui/react-dialog",
    "@radix-ui/react-dropdown-menu",
    "@radix-ui/react-separator",
    "@radix-ui/react-slot",
    "@radix-ui/react-tabs",
    "@radix-ui/react-tooltip",
)


def capability_manifest_for_source(
    source: str,
    *,
    runtime_mode: str,
    interaction_manifest: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic manifest for the imports actually used.

    Deriving declarations from the source prevents a caller from declaring a
    broad capability set that the entry does not use. The compiler still
    validates every import against its own allowlist.
    """
    dependencies: list[str] = []
    for match in re.finditer(r"(?:import|from)\s+[\"']([^\"']+)[\"']", source):
        dependency = match.group(1)
        if dependency in APPROVED_BROWSER_DEPENDENCIES and dependency not in dependencies:
            dependencies.append(dependency)

    uses_webgl = any(
        dependency in {"three", "@react-three/fiber", "@react-three/drei"}
        for dependency in dependencies
    )
    # A Three.js entry is publishable only when the generated code contains a
    # real fallback element/branch. A word in a comment or prose is not
    # evidence that the browser can render anything when WebGL is unavailable.
    has_2d_fallback = _has_real_webgl_fallback(source)
    return {
        "runtimeMode": runtime_mode,
        "dependencies": dependencies,
        "interactionManifest": interaction_manifest or [],
        "webglFallback": (not uses_webgl) or has_2d_fallback,
    }


def _has_real_webgl_fallback(source: str) -> bool:
    """Detect an actual fallback DOM branch, not a comment keyword."""
    without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", " ", source, flags=re.S)
    fallback_element = re.compile(
        r"<(?:svg|canvas|div|figure|img|p|section|span)\b[^>]*(?:"
        r"data-(?:webgl-)?fallback\s*=\s*['\"]?[^>]*|"
        r"(?:className|class|id)\s*=\s*['\"][^'\"]*\b(?:webgl[- ]?)?fallback\b[^'\"]*['\"])[^>]*>",
        re.I,
    )
    if fallback_element.search(without_comments):
        return True

    # Also accept a JSX ternary/conditional whose fallback arm renders an
    # explicit 2D/SVG element. This covers idiomatic `supportsWebGL ? ... :`.
    return bool(
        re.search(
            r"(?:supports?\s*webgl|webgl|renderer)[^\n]{0,180}\?[^\n]{0,260}:\s*<(?:svg|div|figure|canvas|section|span)\b",
            without_comments,
            re.I,
        )
        or re.search(
            r"!\s*(?:supports?\s*webgl|webglAvailable)[^\n]{0,120}&&\s*<(?:svg|div|figure|canvas|section|span)\b",
            without_comments,
            re.I,
        )
    )


def capability_usage_errors(source: str, brief: Any) -> list[str]:
    """Ensure explicitly requested effects have an observable implementation."""
    effects = [str(item).casefold() for item in (getattr(brief, "specialEffects", None) or [])]
    direction = getattr(brief, "creativeDirection", None)
    direction_text = " ".join(
        str(getattr(direction, field, "") or "")
        for field in ("signatureTechnique", "scrollBehavior", "microInteractions")
    ).casefold()
    source_lower = source.casefold()
    errors: list[str] = []
    if any("3d" in effect or "webgl" in effect for effect in effects) or any(
        token in direction_text for token in ("three.js", "webgl", "3d hero")
    ):
        if not any(dependency in source_lower for dependency in ("'three'", '"three"', "'@react-three/", '"@react-three/')):
            errors.append("Brief requests a 3D/WebGL effect but generated code does not use an approved 3D capability")
    if any("parallax" in effect or "scroll" in effect for effect in effects) or "parallax" in direction_text:
        if not re.search(r"scroll|useScroll|scrolltrigger|lenis|parallax", source, re.I):
            errors.append("Brief requests scroll motion but generated code has no scroll interaction")
    if any("cursor" in effect or "magnetic" in effect for effect in effects) or any(
        token in direction_text for token in ("cursor", "magnetic", "pointer")
    ):
        if not re.search(r"pointer|mouse|cursor|onHover|onMouse", source, re.I):
            errors.append("Brief requests cursor interaction but generated code has no pointer interaction")
    return errors


def hero_archetype_errors(
    source: str,
    brief: Any,
    *,
    html: str = "",
    css: str = "",
    js: str = "",
) -> list[str]:
    """Verify that the generated hero visibly implements its selected concept.

    ``heroMode`` answers a safety question (may this hero use approved media?);
    ``heroArchetype`` answers the creative question (what should the visitor
    actually see?). Keeping both contracts prevents every no-photo brief from
    collapsing into the same empty text block while still allowing typography,
    SVG, motion, and WebGL designs.
    """
    archetype = getattr(brief, "heroArchetype", None)
    if not archetype:
        # Older test fixtures and persisted briefs predate the field. Do not
        # make those artifacts fail until they have been rehydrated once.
        return []
    archetype = str(archetype).strip().lower()
    combined = "\n".join((source or "", html or "", css or "", js or ""))
    without_comments = re.sub(r"/\*.*?\*/|//[^\n]*", " ", combined, flags=re.S)
    errors: list[str] = []

    has_hero = bool(
        re.search(
            r"\bhero\b|data-hero|hero-headline|hero-title|<header\b|<h1\b",
            without_comments,
            re.I,
        )
    )
    has_typography = bool(
        re.search(r"<h1\b|\bh1\b|hero-headline|hero-title|data-hero-heading", without_comments, re.I)
    )
    approved_images = [
        str(url).strip()
        for url in list(getattr(getattr(brief, "brandAssets", None), "imageUrls", None) or [])
        if str(url).strip()
    ]
    approved_images.extend(
        str(item.get("url")).strip()
        for item in list(getattr(getattr(brief, "brandAssets", None), "imageInventory", None) or [])
        if isinstance(item, dict) and item.get("url")
    )
    has_approved_photo = bool(approved_images) and any(url in combined for url in approved_images)
    has_svg = bool(re.search(r"<svg\b|createElementNS\s*\(|data-hero-visual|hero[-_ ]diagram", without_comments, re.I))
    has_motion = bool(
        re.search(
            r"@keyframes|\banimation(?:-name)?\s*:|requestAnimationFrame|\bgsap\b|scrolltrigger|\blenis\b|framer-motion|motion\.",
            without_comments,
            re.I,
        )
    )
    has_webgl_import = bool(
        re.search(
            r"(?:from|import\s*\()\s*[\"'](?:three|@react-three/[^\"']+)[\"']|\b(?:three\.js|webgl)\b",
            without_comments,
            re.I,
        )
    )
    has_webgl_fallback = _has_real_webgl_fallback(without_comments)
    modalities = sum((has_approved_photo, has_typography, has_svg, has_motion, has_webgl_import and has_webgl_fallback))

    if archetype == "photography":
        if not has_hero or not has_approved_photo:
            errors.append("Hero archetype 'photography' requires an approved image used in the hero")
    elif archetype == "typography":
        if not has_hero or not has_typography:
            errors.append("Hero archetype 'typography' requires a visible hero heading")
    elif archetype == "svg_diagram":
        if not has_hero or not has_svg:
            errors.append("Hero archetype 'svg_diagram' requires an inline SVG or diagram visual in the hero")
    elif archetype == "motion_graphic":
        if not has_hero or not has_motion:
            errors.append("Hero archetype 'motion_graphic' requires a hero animation or motion implementation")
    elif archetype == "webgl_fallback":
        if not has_webgl_import:
            errors.append("Hero archetype 'webgl_fallback' requires an approved Three.js/WebGL capability")
        elif not has_webgl_fallback:
            errors.append("Hero archetype 'webgl_fallback' requires a real 2D/SVG fallback branch")
    elif archetype == "hybrid":
        if not has_hero or modalities < 2:
            errors.append("Hero archetype 'hybrid' requires at least two visible hero modalities")
    else:
        errors.append(f"Unsupported hero archetype: {archetype}")
    return errors
