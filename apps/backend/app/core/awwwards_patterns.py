"""
Awwwards Pattern Library

Curated design patterns from award-winning websites to inspire and guide
the generation of premium, unique designs.
"""

from __future__ import annotations

from typing import Any, Literal

PatternCategory = Literal[
    "hero", "section", "animation", "layout", "color", "typography"
]


AWWWARDS_PATTERNS: dict[PatternCategory, list[dict[str, Any]]] = {
    "hero": [
        {
            "name": "Split Hero with Video",
            "reference_site": "Active Theory",
            "reference_url": "https://www.awwwards.com/sites/active-theory",
            "description": "50/50 split layout with video on left side and headline + CTA on right. Video plays automatically (muted), creating immediate visual interest.",
            "when_to_use": "Creative agencies, tech startups with demo videos, brands with strong visual identity",
            "key_elements": [
                "Full-height split (60/40 or 50/50)",
                "Autoplay muted video or animated canvas",
                "Large typography (80-120px) on content side",
                "Minimal text: headline + one-line subheadline + CTA",
                "Scroll indicator at bottom",
            ],
            "css_considerations": [
                "Use CSS Grid for split layout",
                "object-fit: cover for video",
                "Ensure video is optimized (max 5MB, VP9/H.264)",
                "Add dark overlay on video for text readability",
            ],
        },
        {
            "name": "Typographic Hero with Gradient Mesh",
            "reference_site": "Stripe",
            "reference_url": "https://stripe.com",
            "description": "Large typographic headline (100-150px) centered on animated gradient mesh background. Pure typography as hero element.",
            "when_to_use": "SaaS, fintech, modern tech brands without strong visual assets",
            "key_elements": [
                "Oversized headline (100-150px on desktop)",
                "Animated mesh gradient background (3-5 colors)",
                "Centered layout with max-width constraint",
                "Short subheadline (20-24px)",
                "Primary + secondary CTA buttons",
            ],
            "css_considerations": [
                "Use CSS custom properties for gradient animation",
                "@keyframes for subtle gradient shift (30s duration)",
                "text-shadow for depth on large text",
                "Responsive typography (clamp() for fluid sizing)",
            ],
        },
        {
            "name": "Parallax Layers Hero",
            "reference_site": "Apple",
            "reference_url": "https://www.apple.com",
            "description": "Multi-layer parallax effect with background, midground, and foreground elements moving at different speeds on scroll.",
            "when_to_use": "Product launches, immersive brand experiences, storytelling sites",
            "key_elements": [
                "3-5 layers with varying scroll speeds",
                "Product image or key visual in midground",
                "Text overlay in foreground",
                "Subtle depth cues (blur, opacity)",
                "Smooth scroll transition to next section",
            ],
            "css_considerations": [
                "Use transform: translateY() for parallax",
                "IntersectionObserver + requestAnimationFrame for performance",
                "will-change: transform on animated elements",
                "Disable on mobile (performance concern)",
            ],
        },
        {
            "name": "Fullscreen Canvas Hero",
            "reference_site": "Bruno Simon",
            "reference_url": "https://bruno-simon.com",
            "description": "Interactive 3D scene (Three.js) or animated canvas as full-screen hero. User can interact (mouse move, click, scroll).",
            "when_to_use": "Creative portfolios, experimental brands, technical showcases",
            "key_elements": [
                "Fullscreen canvas (100vw x 100vh)",
                "Mouse-follow or scroll-triggered interactions",
                "Minimal UI overlay (logo, nav, headline)",
                "Loading indicator for asset loading",
                "Fallback for low-performance devices",
            ],
            "css_considerations": [
                "position: fixed canvas with z-index management",
                "pointer-events: none on overlay content",
                "Use WebGL for 3D, Canvas2D for simpler animations",
                "Performance budget: aim for 60fps",
            ],
        },
        {
            "name": "Asymmetric Split Hero",
            "reference_site": "Awwwards Editorial Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Asymmetric split (60/40 or 70/30) with large serif headline on one side and striking image on the other.",
            "when_to_use": "Editorial sites, legal/finance, consulting, premium services",
            "key_elements": [
                "Asymmetric grid (60/40 is common)",
                "Large serif headline (60-80px)",
                "Professional photography (not stock)",
                "Generous whitespace",
                "Subtle animation on load (fade in + slide up)",
            ],
            "css_considerations": [
                "CSS Grid with fr units for asymmetry",
                "aspect-ratio for image container",
                "Framer Motion for entrance animation",
                "Mobile: stack vertically, image first",
            ],
        },
        {
            "name": "Product Screenshot Hero",
            "reference_site": "Linear",
            "reference_url": "https://linear.app",
            "description": "Centered hero with large product screenshot, subtle gradient background, and clear value proposition.",
            "when_to_use": "SaaS products, mobile apps, software tools with strong UI",
            "key_elements": [
                "Centered layout with product screenshot (70% width)",
                "Gradient background (2-3 colors, subtle)",
                "Headline above screenshot (40-60px)",
                "Screenshot has shadow/glow for depth",
                "CTA buttons below screenshot",
            ],
            "css_considerations": [
                "box-shadow with blur for depth",
                "background: linear-gradient with alpha",
                "Image optimization (use WebP, lazy load)",
                "Add slight upward animation on load",
            ],
        },
        {
            "name": "Carousel Hero",
            "reference_site": "E-commerce Fashion Sites",
            "reference_url": "https://www.gucci.com",
            "description": "Auto-rotating carousel of hero images with text overlays. Manual controls (dots, arrows) for user navigation.",
            "when_to_use": "E-commerce, fashion, portfolios with multiple hero-worthy visuals",
            "key_elements": [
                "3-5 slides, auto-rotate every 5-7 seconds",
                "Full-bleed images with text overlay",
                "Navigation dots at bottom",
                "Prev/next arrows on hover",
                "Pause on hover or user interaction",
            ],
            "css_considerations": [
                "Use Embla Carousel or Swiper for accessibility",
                "transition: transform 0.6s ease for smooth slides",
                "Preload next image for instant transition",
                "aria-live for screen readers",
            ],
        },
        {
            "name": "Minimal Centered Hero",
            "reference_site": "Minimalist Portfolios",
            "reference_url": "https://www.awwwards.com/websites/minimal/",
            "description": "Minimal centered text (headline + subheadline + CTA) with subtle background (gradient, grain, or solid color). No images.",
            "when_to_use": "Minimalist brands, text-first sites, when brand identity is strong enough without visuals",
            "key_elements": [
                "Centered text block (max 800px width)",
                "Large headline (60-100px)",
                "Ample whitespace (2-3x line-height)",
                "Subtle animation (fade in, no jarring motion)",
                "Single CTA button",
            ],
            "css_considerations": [
                "background with subtle texture (grain overlay at 5% opacity)",
                "Generous line-height (1.4-1.6)",
                "letter-spacing on headline (-0.02em for tight tracking)",
                "Mobile: reduce font-size proportionally",
            ],
        },
    ],
    "section": [
        {
            "name": "Bento Grid with Hover Lift",
            "reference_site": "Apple Vision Pro",
            "reference_url": "https://www.apple.com/apple-vision-pro/",
            "description": "Asymmetric grid (varied cell sizes) where cards lift on hover with shadow. Used for feature showcases.",
            "when_to_use": "Feature showcases, service listings, content grids with varying importance",
            "key_elements": [
                "CSS Grid with varied cell sizes (span 2, span 3, etc.)",
                "Cards lift 8-12px on hover",
                "Shadow increases on hover",
                "Stagger animation on scroll (each card fades in sequentially)",
                "Each card has icon/image + headline + short description",
            ],
            "css_considerations": [
                "grid-template-columns: repeat(auto-fit, minmax(300px, 1fr))",
                "transform: translateY(-8px) on hover",
                "transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                "Use Framer Motion variants for stagger",
            ],
        },
        {
            "name": "Horizontal Scroll Gallery",
            "reference_site": "Various Portfolio Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Horizontal scroll section (left to right) for showcasing portfolio items, products, or timeline.",
            "when_to_use": "Portfolios, product showcases, timelines, case studies",
            "key_elements": [
                "Container with overflow-x: scroll (smooth snap)",
                "Items displayed in horizontal row",
                "Scroll-snap-type for smooth stops",
                "Indicator showing scroll progress",
                "Works with mouse drag and touch",
            ],
            "css_considerations": [
                "scroll-snap-type: x mandatory",
                "scroll-behavior: smooth",
                "overflow-x: auto with custom scrollbar",
                "Use Embla Carousel for enhanced control",
            ],
        },
        {
            "name": "Full-Bleed Image with Text Overlay",
            "reference_site": "Editorial Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Full-width image section with text overlay (often used for testimonials, quotes, or section breaks).",
            "when_to_use": "Testimonials, brand statements, section dividers",
            "key_elements": [
                "Full-width image (100vw)",
                "Dark overlay (opacity 0.4-0.6) for text readability",
                "Large quote or headline centered",
                "Parallax or Ken Burns effect on image",
            ],
            "css_considerations": [
                "background-attachment: fixed for parallax (careful with mobile)",
                "Dark gradient overlay for readability",
                "text-shadow for additional contrast",
                "Optimize image (lazy load, srcset)",
            ],
        },
        {
            "name": "Feature Comparison Table",
            "reference_site": "SaaS Pricing Pages",
            "reference_url": "https://linear.app/pricing",
            "description": "Interactive comparison table with column highlighting on hover. Used for pricing tiers or feature comparisons.",
            "when_to_use": "SaaS pricing, feature comparisons, product tiers",
            "key_elements": [
                "3-column layout (Free, Pro, Enterprise)",
                "Middle column highlighted by default",
                "Checkmarks/X for feature availability",
                "Column highlights on hover",
                "Sticky header on scroll",
            ],
            "css_considerations": [
                "position: sticky on header row",
                "background-color transition on hover",
                "Use semantic table markup for accessibility",
                "Mobile: horizontal scroll or accordion",
            ],
        },
        {
            "name": "Testimonial Carousel with Avatars",
            "reference_site": "SaaS Sites",
            "reference_url": "https://www.vercel.com",
            "description": "Testimonial carousel with customer avatar, quote, name, and company. Auto-rotates with manual controls.",
            "when_to_use": "Social proof sections, client testimonials, case study quotes",
            "key_elements": [
                "Large quote (24-32px)",
                "Customer avatar (circular, 60-80px)",
                "Name + title + company below quote",
                "Star rating or logo if available",
                "Dots navigation + auto-rotate",
            ],
            "css_considerations": [
                "Use Embla Carousel for accessibility",
                "fade transition instead of slide for testimonials",
                "Generous padding for readability",
                "Consider static grid on mobile (no carousel)",
            ],
        },
        {
            "name": "Stats Counter Section",
            "reference_site": "Corporate Sites",
            "reference_url": "https://www.stripe.com",
            "description": "Section with animated count-up numbers (triggered on scroll) showing key metrics.",
            "when_to_use": "Proof sections, company stats, impact metrics",
            "key_elements": [
                "3-4 large numbers (60-80px)",
                "Count-up animation from 0 to target",
                "Short label below each number",
                "Triggered when section enters viewport",
                "Runs once per page load",
            ],
            "css_considerations": [
                "IntersectionObserver to trigger animation",
                "CountUp.js or custom JavaScript animation",
                "Use monospace font for numbers (prevents layout shift)",
                "Add easing for satisfying feel (easeOutExpo)",
            ],
        },
    ],
    "animation": [
        {
            "name": "Stagger Fade-In on Scroll",
            "reference_site": "Linear",
            "reference_url": "https://linear.app",
            "description": "Grid items fade in sequentially (staggered) as user scrolls into section.",
            "when_to_use": "Any grid or list section (features, services, team, portfolio)",
            "key_elements": [
                "Each item starts at opacity: 0, translateY: 20px",
                "Items animate in order with 0.1s delay between each",
                "Triggered when section enters viewport",
                "Uses cubic-bezier easing for smooth motion",
            ],
            "css_considerations": [
                "Use Framer Motion variants with staggerChildren",
                "IntersectionObserver with viewport: { once: true }",
                "Delay between items: 0.08-0.15s (faster feels snappier)",
                "Consider reducing motion for accessibility",
            ],
        },
        {
            "name": "Magnetic Button",
            "reference_site": "Creative Portfolios",
            "reference_url": "https://www.awwwards.com",
            "description": "Button follows cursor when mouse is nearby, creating magnetic attraction effect.",
            "when_to_use": "Primary CTAs on creative/experimental sites, portfolio sites",
            "key_elements": [
                "Button follows cursor within radius (80-120px)",
                "Smooth easing (not instant snap)",
                "Returns to center when cursor leaves radius",
                "Can include scale-up on hover",
            ],
            "css_considerations": [
                "Use JavaScript to track mouse position",
                "transform: translate() to move button",
                "transition with spring physics (or GSAP)",
                "Disable on mobile (no mouse tracking)",
            ],
        },
        {
            "name": "Scroll-Linked Progress Bar",
            "reference_site": "Various",
            "reference_url": "https://www.awwwards.com",
            "description": "Progress bar at top of page that fills as user scrolls down.",
            "when_to_use": "Long-form content, blog posts, case studies",
            "key_elements": [
                "Fixed position bar at top (2-4px height)",
                "Width increases based on scroll percentage",
                "Smooth transition (no jumps)",
                "Brand color for bar",
            ],
            "css_considerations": [
                "position: fixed with z-index above content",
                "Calculate percentage: scrollTop / (scrollHeight - clientHeight)",
                "Use transform: scaleX() for better performance",
                "Update on requestAnimationFrame or scroll event (throttled)",
            ],
        },
        {
            "name": "Parallax Scroll Effect",
            "reference_site": "Apple, Various",
            "reference_url": "https://www.apple.com",
            "description": "Background elements move slower than foreground on scroll, creating depth.",
            "when_to_use": "Hero sections, full-bleed images, storytelling sites",
            "key_elements": [
                "Background moves at 0.3-0.5x scroll speed",
                "Foreground at 1x (normal scroll)",
                "Subtle effect (not exaggerated)",
                "Disabled on mobile for performance",
            ],
            "css_considerations": [
                "Use transform: translateY() for smooth motion",
                "Avoid background-attachment: fixed (mobile issues)",
                "requestAnimationFrame for smooth updates",
                "Consider Intersection Observer to limit active parallax",
            ],
        },
        {
            "name": "Hover Reveal Effect",
            "reference_site": "Portfolio Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Image reveals on hover (grayscale to color, or overlay fade out).",
            "when_to_use": "Portfolio grids, team photos, image galleries",
            "key_elements": [
                "Default state: grayscale filter or color overlay",
                "Hover state: full color revealed",
                "Smooth transition (0.3-0.5s)",
                "Optional: scale-up on hover (1.05x)",
            ],
            "css_considerations": [
                "filter: grayscale(100%) on default",
                "filter: grayscale(0%) on hover",
                "transition: all 0.4s ease",
                "Add transform: scale(1.05) for extra polish",
            ],
        },
    ],
    "layout": [
        {
            "name": "Asymmetric Grid",
            "reference_site": "Editorial Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Grid with varied cell sizes (not uniform), creating visual interest and hierarchy.",
            "when_to_use": "Feature showcases, content grids, portfolio layouts",
            "key_elements": [
                "CSS Grid with mixed column spans",
                "Some cells span 2 columns, others 1",
                "Varied row heights based on content",
                "Responsive: collapses to single column on mobile",
            ],
            "css_considerations": [
                "grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))",
                "Use grid-column: span 2 for feature items",
                "gap: 1.5rem for breathing room",
                "Consider masonry layout for varied heights",
            ],
        },
        {
            "name": "Diagonal Split Section",
            "reference_site": "Creative Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Section split diagonally (not horizontally), creating dynamic visual break.",
            "when_to_use": "Section dividers, about sections, brand storytelling",
            "key_elements": [
                "Diagonal line separating two halves",
                "Each half has different background color/image",
                "Content aligned to each side",
                "Angle typically 5-15 degrees",
            ],
            "css_considerations": [
                "clip-path: polygon() for diagonal cut",
                "Or use transform: skewY() on pseudo-element",
                "Mobile: remove diagonal, stack vertically",
                "Example: clip-path: polygon(0 0, 100% 10%, 100% 100%, 0 90%)",
            ],
        },
        {
            "name": "Sticky Sidebar Navigation",
            "reference_site": "Documentation Sites",
            "reference_url": "https://vercel.com/docs",
            "description": "Sidebar navigation that sticks to viewport as user scrolls, highlighting current section.",
            "when_to_use": "Documentation, long-form content, multi-section pages",
            "key_elements": [
                "Sidebar fixed to left (or right)",
                "Navigation links highlight based on scroll position",
                "Smooth scroll to section on click",
                "Compact on mobile (hamburger or hidden)",
            ],
            "css_considerations": [
                "position: sticky with top: 0",
                "IntersectionObserver to detect active section",
                "smooth scroll-behavior on clicks",
                "Mobile: convert to top bar or drawer",
            ],
        },
        {
            "name": "Full-Bleed Sections",
            "reference_site": "Modern Sites",
            "reference_url": "https://www.stripe.com",
            "description": "Sections that extend edge-to-edge (no side padding), alternating with constrained sections.",
            "when_to_use": "Modern, impactful designs, image-heavy sections",
            "key_elements": [
                "Alternating full-width and constrained sections",
                "Full-width sections use 100vw",
                "Constrained sections have max-width (1200px)",
                "Creates rhythm and visual interest",
            ],
            "css_considerations": [
                "Full-bleed: width: 100vw; margin-left: calc(-50vw + 50%)",
                "Or use CSS Grid with full-width tracks",
                "Be careful with horizontal overflow",
                "Consider using container queries for nested layouts",
            ],
        },
    ],
    "color": [
        {
            "name": "Mesh Gradient Background",
            "reference_site": "Stripe, Modern SaaS",
            "reference_url": "https://stripe.com",
            "description": "Animated multi-color gradient with blur, creating organic flowing background.",
            "when_to_use": "Hero backgrounds, section backgrounds for modern/tech brands",
            "key_elements": [
                "3-5 gradient colors from brand palette",
                "Multiple radial gradients overlapped",
                "Subtle animation (very slow, 30-60s)",
                "Blur filter for soft blend",
            ],
            "css_considerations": [
                "Multiple background-image radial gradients",
                "filter: blur(80px) for soft effect",
                "@keyframes to shift gradient positions",
                "Use CSS custom properties for color control",
            ],
        },
        {
            "name": "Duotone Image Overlay",
            "reference_site": "Creative Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Images with two-color overlay (replaces shadows/highlights with brand colors).",
            "when_to_use": "Hero images, portfolio thumbnails, team photos",
            "key_elements": [
                "Image converted to two-tone (dark + light from brand palette)",
                "blend-mode for color mixing",
                "Maintains contrast and recognizability",
            ],
            "css_considerations": [
                "background-blend-mode: multiply + lighten",
                "Or use CSS filter: sepia() + hue-rotate()",
                "SVG feColorMatrix for precise control",
                "Example: filter: grayscale(100%) sepia(100%) hue-rotate(180deg)",
            ],
        },
        {
            "name": "Dark Mode with Neon Accents",
            "reference_site": "Creative/Tech Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Dark background (near-black) with vibrant neon accent colors for CTAs and highlights.",
            "when_to_use": "Creative agencies, tech products, gaming, nightlife",
            "key_elements": [
                "Background: #0a0a0a to #1a1a1a",
                "Text: #e0e0e0 (not pure white)",
                "Accents: cyan, magenta, lime, electric blue",
                "Glow effects on accents (box-shadow with color)",
            ],
            "css_considerations": [
                "Use HSL for accent colors (easy to adjust)",
                "box-shadow: 0 0 20px rgba(accent, 0.5) for glow",
                "Avoid pure black (use #0a0a0a)",
                "Ensure WCAG contrast ratios (text on dark)",
            ],
        },
    ],
    "typography": [
        {
            "name": "Mixed Serif + Sans Pairing",
            "reference_site": "Editorial Sites",
            "reference_url": "https://www.nytimes.com",
            "description": "Large serif headlines paired with clean sans-serif body text.",
            "when_to_use": "Editorial sites, legal/finance, premium brands",
            "key_elements": [
                "Serif for headlines (60-120px): Tiempos, Crimson, Freight Display",
                "Sans for body (16-18px): Inter, Helvetica, Circular",
                "High contrast between display and body",
                "Generous line-height (1.6-1.8 for body)",
            ],
            "css_considerations": [
                "font-family: 'Tiempos', Georgia, serif for headings",
                "font-family: 'Inter', system-ui, sans-serif for body",
                "Use font-display: swap for web fonts",
                "letter-spacing: -0.02em on large headlines",
            ],
        },
        {
            "name": "Oversized Display Type",
            "reference_site": "Creative Sites",
            "reference_url": "https://www.awwwards.com",
            "description": "Extremely large headline typography (120-200px) as a primary design element.",
            "when_to_use": "Creative agencies, bold brands, minimalist sites",
            "key_elements": [
                "Headlines: 100-200px on desktop",
                "Tight letter-spacing (-0.03em to -0.05em)",
                "Often uses display serif or bold sans",
                "Responsive: use clamp() for fluid sizing",
            ],
            "css_considerations": [
                "font-size: clamp(3rem, 10vw, 12rem)",
                "line-height: 0.9-1.1 (tight leading)",
                "letter-spacing: -0.04em",
                "font-weight: 700-900 for sans, 400-600 for serif",
            ],
        },
        {
            "name": "Monospace for Technical Content",
            "reference_site": "Developer Tools",
            "reference_url": "https://vercel.com",
            "description": "Monospace fonts for code snippets, technical specs, and developer-focused content.",
            "when_to_use": "Developer tools, technical products, API documentation",
            "key_elements": [
                "Monospace: JetBrains Mono, Fira Code, SF Mono",
                "Use for code blocks, inline code, and technical data",
                "Syntax highlighting for code examples",
                "Dark background for code blocks",
            ],
            "css_considerations": [
                "font-family: 'JetBrains Mono', 'Courier New', monospace",
                "Background: #1a1a1a for code blocks",
                "Padding: 1rem for readability",
                "overflow-x: auto for long lines",
            ],
        },
    ],
}


def get_patterns_for_industry(
    industry: str, categories: list[PatternCategory] | None = None
) -> list[dict[str, Any]]:
    """Get relevant patterns for a specific industry."""

    # Industry-to-pattern mapping
    industry_pattern_map = {
        "creative_agency": {
            "hero": [
                "Split Hero with Video",
                "Fullscreen Canvas Hero",
                "Typographic Hero with Gradient Mesh",
            ],
            "section": ["Bento Grid with Hover Lift", "Horizontal Scroll Gallery"],
            "animation": [
                "Magnetic Button",
                "Stagger Fade-In on Scroll",
                "Hover Reveal Effect",
            ],
            "layout": ["Asymmetric Grid", "Full-Bleed Sections"],
            "color": ["Mesh Gradient Background", "Dark Mode with Neon Accents"],
            "typography": ["Oversized Display Type", "Mixed Serif + Sans Pairing"],
        },
        "saas": {
            "hero": ["Product Screenshot Hero", "Typographic Hero with Gradient Mesh"],
            "section": [
                "Feature Comparison Table",
                "Stats Counter Section",
                "Testimonial Carousel with Avatars",
            ],
            "animation": ["Stagger Fade-In on Scroll", "Scroll-Linked Progress Bar"],
            "layout": ["Full-Bleed Sections", "Sticky Sidebar Navigation"],
            "color": ["Mesh Gradient Background"],
            "typography": ["Mixed Serif + Sans Pairing"],
        },
        "legal_finance": {
            "hero": ["Asymmetric Split Hero", "Minimal Centered Hero"],
            "section": ["Full-Bleed Image with Text Overlay", "Stats Counter Section"],
            "animation": ["Stagger Fade-In on Scroll"],
            "layout": ["Asymmetric Grid"],
            "color": [],
            "typography": ["Mixed Serif + Sans Pairing"],
        },
        "ecommerce_fashion": {
            "hero": ["Carousel Hero", "Parallax Layers Hero"],
            "section": [
                "Horizontal Scroll Gallery",
                "Full-Bleed Image with Text Overlay",
            ],
            "animation": ["Hover Reveal Effect", "Parallax Scroll Effect"],
            "layout": ["Full-Bleed Sections", "Asymmetric Grid"],
            "color": ["Duotone Image Overlay"],
            "typography": ["Oversized Display Type"],
        },
        "tech": {
            "hero": ["Typographic Hero with Gradient Mesh", "Fullscreen Canvas Hero"],
            "section": ["Feature Comparison Table", "Stats Counter Section"],
            "animation": ["Stagger Fade-In on Scroll", "Scroll-Linked Progress Bar"],
            "layout": ["Full-Bleed Sections", "Sticky Sidebar Navigation"],
            "color": ["Mesh Gradient Background", "Dark Mode with Neon Accents"],
            "typography": ["Monospace for Technical Content", "Oversized Display Type"],
        },
    }

    # Get patterns for industry (or use default)
    pattern_names = industry_pattern_map.get(
        industry,
        {
            "hero": ["Typographic Hero with Gradient Mesh", "Asymmetric Split Hero"],
            "section": ["Bento Grid with Hover Lift", "Stats Counter Section"],
            "animation": ["Stagger Fade-In on Scroll"],
            "layout": ["Full-Bleed Sections"],
            "color": ["Mesh Gradient Background"],
            "typography": ["Mixed Serif + Sans Pairing"],
        },
    )

    # Filter by categories if specified
    if categories:
        pattern_names = {k: v for k, v in pattern_names.items() if k in categories}

    # Collect matching patterns
    selected_patterns = []
    for category_str, names in pattern_names.items():
        # Validate category
        if category_str not in [
            "hero",
            "section",
            "animation",
            "layout",
            "color",
            "typography",
        ]:
            continue
        category: PatternCategory = category_str  # type: ignore
        for pattern in AWWWARDS_PATTERNS.get(category, []):
            if pattern["name"] in names:
                selected_patterns.append(
                    {
                        **pattern,
                        "category": category,
                    }
                )

    return selected_patterns


def build_pattern_context_for_llm(industry: str, section_type: str = "hero") -> str:
    """Build pattern reference context for LLM prompts."""

    # Map section types to pattern categories
    category_map = {
        "hero": ["hero"],
        "services": ["section", "layout"],
        "about": ["section", "typography"],
        "proof": ["section", "animation"],
        "process": ["section", "layout"],
        "pricing": ["section"],
        "team": ["section", "animation"],
        "contact": ["section"],
    }

    categories = category_map.get(section_type, ["section"])
    patterns = get_patterns_for_industry(industry, categories)  # type: ignore

    if not patterns:
        return ""

    context = "# AWWWARDS REFERENCE PATTERNS\n\n"
    context += (
        f"Here are award-winning design patterns relevant to {industry} websites:\n\n"
    )

    for i, pattern in enumerate(patterns[:3], 1):  # Limit to top 3 patterns
        context += f"## Pattern {i}: {pattern['name']}\n"
        context += f"**Reference:** {pattern.get('reference_site', 'N/A')}\n"
        context += f"**Description:** {pattern['description']}\n"
        context += f"**When to use:** {pattern['when_to_use']}\n"
        if pattern.get("key_elements"):
            context += "**Key elements:**\n"
            for elem in pattern["key_elements"]:
                context += f"- {elem}\n"
        context += "\n"

    context += "Use these patterns as inspiration. Adapt them to fit the specific content and brand.\n\n"

    return context


def get_hero_pattern_recommendation(
    industry: str, available_assets: dict[str, bool]
) -> dict[str, Any]:
    """Recommend a specific hero pattern based on industry and available assets."""

    patterns = get_patterns_for_industry(industry, ["hero"])

    # Filter based on available assets
    if available_assets.get("has_video"):
        # Prefer video-based heroes
        for pattern in patterns:
            if "Video" in pattern["name"]:
                return pattern

    if available_assets.get("has_product_image"):
        # Prefer product screenshot heroes
        for pattern in patterns:
            if "Product" in pattern["name"]:
                return pattern

    if (
        available_assets.get("has_hero_images")
        and available_assets.get("image_count", 0) > 3
    ):
        # Prefer carousel if multiple images
        for pattern in patterns:
            if "Carousel" in pattern["name"]:
                return pattern

    # Default to first pattern for industry
    return (
        patterns[0]
        if patterns
        else {
            "name": "Typographic Hero with Gradient Mesh",
            "description": "Fallback hero pattern",
            "key_elements": [],
        }
    )
