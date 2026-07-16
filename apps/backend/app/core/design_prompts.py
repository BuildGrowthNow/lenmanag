"""
Industry-Specific Design Prompts

Custom visual redesign prompts for each industry with reference examples
and specific design direction.
"""

from __future__ import annotations

from typing import Any


INDUSTRY_DESIGN_PROMPTS: dict[str, dict[str, Any]] = {
    "creative_agency": {
        "visual_brief_prompt": """You are a premium web designer creating a portfolio site for a creative agency.

DESIGN DIRECTION:
- Bold, experimental, portfolio-first approach
- Large typography (80-150px headlines) as a design element
- Dark theme with vibrant accent colors (cyan, magenta, lime)
- Interactive elements and scroll-triggered reveals
- Focus on showcasing work dramatically

REFERENCE STYLE:
Think: Awwwards winners like Active Theory, Bruno Simon
- Full-screen immersive experiences
- Case study deep-dives with rich media
- Experimental layouts (asymmetric grids, overlapping elements)
- Motion as a core design language

HERO APPROACH:
- Full-screen video or animated canvas background
- Minimal text overlay (just company name + powerful tagline)
- Immediate visual impact over explanation

SECTIONS TO EMPHASIZE:
- Portfolio grid (filterable, large thumbnails)
- Case study showcases (dedicated pages/modals)
- Awards/press mentions
- Team profiles with personality

TONE:
Confident, cutting-edge, "we don't follow trends, we set them"

WHAT TO AVOID:
- Generic "we help businesses" language
- Stock photography
- Corporate formality
- Lengthy explanations""",
        "content_rewrite_instructions": """Rewrite for IMPACT and CONFIDENCE:
- Use power verbs: "Transform", "Craft", "Architect", "Unleash"
- Be bold, not humble: "We create award-winning digital experiences"
- Cut all filler words and clichés
- Make every sentence earn its place
- Speak to creative leaders and brand managers""",
    },
    "saas": {
        "visual_brief_prompt": """You are designing a modern SaaS product website.

DESIGN DIRECTION:
- Clean, functional, data-driven aesthetic
- Light theme with bold primary color (blue, purple, green)
- Clear visual hierarchy and grid-based layouts
- Product screenshots as hero elements
- Trust signals and social proof prominently displayed

REFERENCE STYLE:
Think: Linear, Stripe, Vercel, Notion
- Product-first design
- Subtle animations (fade-in, lift on hover)
- Feature comparison tables
- Integration logo grids

HERO APPROACH:
- Centered layout with product screenshot
- Clear value proposition (one sentence)
- Gradient background (subtle, not overwhelming)
- Primary CTA prominent

SECTIONS TO EMPHASIZE:
- Feature comparison table
- Pricing tiers (3 columns, middle highlighted)
- Integration logos (show ecosystem)
- Live metrics/testimonials with real data

TONE:
Professional, efficient, "get more done with less effort"

WHAT TO AVOID:
- Overly creative/experimental layouts
- Dark themes (unless explicitly requested)
- Lengthy copy blocks
- Abstract concepts without concrete benefits""",
        "content_rewrite_instructions": """Rewrite for CLARITY and VALUE:
- Lead with the benefit, not the feature
- Use metrics: "10x faster" not "very fast"
- Be specific: "Ship in 5 minutes" not "Deploy quickly"
- Address pain points directly
- Speak to product managers and technical buyers""",
    },
    "legal_finance": {
        "visual_brief_prompt": """You are designing a professional services website for legal or financial services.

DESIGN DIRECTION:
- Authoritative, editorial, trust-focused
- Light theme with navy, charcoal, or muted blue
- Strong typography (serif display + sans body)
- Professional photography (real people, not stock)
- Case results and credentials front and center

REFERENCE STYLE:
Think: Premium law firms, investment firms
- Editorial layouts (split 50/50, large headlines)
- Content-rich (case studies, insights)
- Professional without being boring
- Trust signals everywhere (certifications, results, tenure)

HERO APPROACH:
- Split editorial layout (60/40)
- Large serif headline with authority
- Professional image on one side
- Immediate credibility signals

SECTIONS TO EMPHASIZE:
- Practice areas/services (detailed)
- Notable cases/results (with outcomes)
- Team credentials (education, experience)
- Client testimonials (with real names/companies)

TONE:
Authoritative, experienced, "we've seen it all and won"

WHAT TO AVOID:
- Playful language or casual tone
- Bright colors or experimental layouts
- Abstract imagery
- Over-animation or motion""",
        "content_rewrite_instructions": """Rewrite for AUTHORITY and PRECISION:
- Use industry-specific terminology correctly
- Emphasize experience: "Three decades of trial experience"
- Be specific about outcomes: "$50M recovered for clients"
- Formal but not stuffy
- Speak to business leaders and general counsel""",
    },
    "ecommerce_fashion": {
        "visual_brief_prompt": """You are designing an e-commerce fashion site.

DESIGN DIRECTION:
- Visual-first, immersive, product photography dominant
- Monochrome (black/white) + one brand accent color
- Minimalist typography (Helvetica, Futura)
- Large product images (full-bleed sections)
- Editorial lookbook aesthetic

REFERENCE STYLE:
Think: Awwwards e-commerce like Gucci, Nike concepts
- Product carousel as hero
- Grid layouts with hover zoom
- Minimal text overlay on images
- Instagram-like visual feed

HERO APPROACH:
- Full-bleed product video or carousel
- Minimal text (just brand + "Shop Now")
- Let products speak for themselves

SECTIONS TO EMPHASIZE:
- Lookbook grid (2-3 column, varying heights)
- Product carousel (auto-rotate with manual controls)
- Instagram feed integration
- Size guide/styling tips

TONE:
Aspirational, style-conscious, "elevated everyday"

WHAT TO AVOID:
- Busy layouts with too much text
- Multiple competing CTAs
- Complex navigation
- Over-explanation of products""",
        "content_rewrite_instructions": """Rewrite for ASPIRATION and BREVITY:
- Use sensory language: "Buttery soft leather"
- Create desire, not just describe
- Keep it minimal: 1-2 sentences max
- Focus on lifestyle, not just product
- Speak to style-conscious consumers""",
    },
    "consulting": {
        "visual_brief_prompt": """You are designing a consulting firm website.

DESIGN DIRECTION:
- Professional, strategic, results-focused
- Light theme with professional color (blue, teal, slate)
- Data visualization and metrics prominent
- Case study driven
- Clear value proposition

REFERENCE STYLE:
Think: McKinsey, Bain, Deloitte Digital
- Clean grid layouts
- Process/methodology diagrams
- Before/after metrics
- Client logo grids

HERO APPROACH:
- Split or centered layout
- Value-driven headline
- Specific outcome metrics
- Professional imagery (office, team, data)

SECTIONS TO EMPHASIZE:
- Services grid (icon + short description)
- Case studies (industry + challenge + result)
- Methodology/process visualization
- Insights/thought leadership

TONE:
Strategic, results-driven, "we solve complex problems"

WHAT TO AVOID:
- Vague language ("we help businesses succeed")
- Abstract concepts without examples
- Over-creative layouts
- Lengthy paragraphs""",
        "content_rewrite_instructions": """Rewrite for RESULTS and SPECIFICITY:
- Lead with outcomes: "Reduced costs by 40%"
- Use consulting frameworks (strategy, transformation, etc.)
- Be metric-driven
- Show ROI explicitly
- Speak to C-suite and VPs""",
    },
    "real_estate": {
        "visual_brief_prompt": """You are designing a real estate website.

DESIGN DIRECTION:
- Clean, aspirational, property-focused
- Light theme with earthy or professional accent
- High-quality property photography
- Map integration prominent
- Search/filter functionality clear

REFERENCE STYLE:
Think: Premium real estate agencies
- Property grid with key details overlay
- Neighborhood/location showcases
- Agent profiles with personality
- Virtual tour integration

HERO APPROACH:
- Parallax property images
- Location-based headline
- Quick search/filter bar
- Featured properties showcase

SECTIONS TO EMPHASIZE:
- Featured properties (grid with key stats)
- Neighborhood guides (walkability, schools, etc.)
- Agent profiles (with track record)
- Client testimonials (with sale prices)

TONE:
Aspirational, knowledgeable, "home is where life happens"

WHAT TO AVOID:
- Generic stock real estate imagery
- Overly salesy language
- Cluttered layouts with too many filters
- Ignoring location/neighborhood context""",
        "content_rewrite_instructions": """Rewrite for ASPIRATION and LOCAL EXPERTISE:
- Emphasize location benefits
- Use lifestyle language: "Morning coffee on your private terrace"
- Show local knowledge
- Include specific metrics (sqft, beds/baths)
- Speak to homebuyers and sellers""",
    },
    "health_wellness": {
        "visual_brief_prompt": """You are designing a health/wellness website.

DESIGN DIRECTION:
- Warm, trustworthy, human-centered
- Light theme with soft colors (green, teal, warm neutrals)
- Approachable photography (real people, not stock)
- Clear information hierarchy
- Accessibility is paramount

REFERENCE STYLE:
Think: Modern healthcare brands
- Service-focused layouts
- Practitioner profiles with credentials and warmth
- Before/after patient stories
- Appointment booking prominent

HERO APPROACH:
- Centered with welcoming image
- Compassionate headline
- Clear service offering
- Easy booking CTA

SECTIONS TO EMPHASIZE:
- Services overview (with what to expect)
- Practitioner bios (credentials + personality)
- Patient testimonials (with real names/photos)
- Appointment booking (frictionless)

TONE:
Compassionate, professional, "we care about your wellbeing"

WHAT TO AVOID:
- Clinical/cold aesthetic
- Overly technical language
- Dark themes
- Aggressive animations""",
        "content_rewrite_instructions": """Rewrite for COMPASSION and CLARITY:
- Use warm, approachable language
- Explain medical terms simply
- Focus on patient outcomes
- Address common concerns directly
- Speak to patients and their families""",
    },
    "tech": {
        "visual_brief_prompt": """You are designing a tech company website.

DESIGN DIRECTION:
- Modern, innovative, technical aesthetic
- Dark theme with vibrant accent (purple, cyan, neon)
- Abstract/geometric visuals
- Developer-focused when appropriate
- Technical details visible but not overwhelming

REFERENCE STYLE:
Think: Vercel, Railway, HashiCorp
- Dark mode default
- Animated gradient backgrounds
- Code snippets and technical diagrams
- GitHub stars/open source badges

HERO APPROACH:
- Animated gradient mesh background
- Technical but accessible headline
- Product/tech screenshot or diagram
- "Get Started" + "View Docs" CTAs

SECTIONS TO EMPHASIZE:
- Technology stack (logos + descriptions)
- Use cases (with code examples)
- Documentation/API reference links
- Developer resources (SDKs, integrations)

TONE:
Innovative, technical, "built by developers for developers"

WHAT TO AVOID:
- Overly salesy corporate language
- Light themes (unless specifically requested)
- Non-technical explanations for technical products
- Ignoring developer experience""",
        "content_rewrite_instructions": """Rewrite for TECHNICAL CLARITY and INNOVATION:
- Use technical terms correctly
- Show code examples when relevant
- Be precise about capabilities
- Emphasize developer experience
- Speak to engineers and technical leads""",
    },
}


def get_industry_design_prompt(industry: str) -> dict[str, str]:
    """Get the design prompt configuration for an industry."""
    return INDUSTRY_DESIGN_PROMPTS.get(
        industry,
        {
            "visual_brief_prompt": """You are a premium web designer creating a modern website.

DESIGN DIRECTION:
- Clean, modern, professional aesthetic
- Clear visual hierarchy
- Industry-appropriate color palette
- Trust signals and credibility markers

HERO APPROACH:
- Clear value proposition
- Professional imagery
- Prominent CTA

SECTIONS TO EMPHASIZE:
- Services/offerings
- About/credentials
- Testimonials/proof
- Contact/CTA

TONE:
Professional, trustworthy, clear

WHAT TO AVOID:
- Generic stock imagery
- Vague language
- Cluttered layouts""",
            "content_rewrite_instructions": """Rewrite for CLARITY and IMPACT:
- Be specific and concrete
- Lead with benefits
- Remove filler words
- Use active voice
- Speak to your target audience""",
        },
    )


def build_visual_redesign_prompt(
    industry: str,
    company_name: str,
    mission: str,
    services: list[str],
    tone_clues: list[str],
    extracted_content: str,
) -> str:
    """Build a complete visual redesign prompt with industry-specific guidance."""

    design_config = get_industry_design_prompt(industry)

    prompt = f"""You are tasked with creating a visual redesign brief for a premium website.

# COMPANY CONTEXT
Company: {company_name}
Mission: {mission}
Services: {", ".join(services[:5])}
Tone: {", ".join(tone_clues[:3])}

# INDUSTRY: {industry.upper()}

{design_config["visual_brief_prompt"]}

# SOURCE CONTENT (for context only, will be rewritten)
{extracted_content[:500]}...

# YOUR TASK
Create a visual redesign brief that includes:
1. Overall design direction (3-4 sentences)
2. Hero section approach (specific layout and content)
3. Key section recommendations (which sections, in what order)
4. Typography and color guidance
5. Animation/motion recommendations

Be specific and actionable. Think like an award-winning web designer.
"""

    return prompt


def build_content_rewrite_prompt(
    industry: str,
    content_type: str,  # "headline", "subheadline", "service", "cta", "body"
    original_content: str,
    company_name: str,
    brand_tone: str,
) -> str:
    """Build a content rewriting prompt for specific content types."""

    design_config = get_industry_design_prompt(industry)

    content_type_specs = {
        "headline": {
            "goal": "Create a powerful, memorable headline that captures attention in 5-8 words",
            "constraints": "Max 60 characters, front-load the value",
            "examples": {
                "creative_agency": '"We craft digital experiences that convert" (not "We are a creative agency")',
                "saas": '"Ship 10x faster with zero config" (not "Our platform helps you build")',
                "legal_finance": '"Three decades defending Fortune 500 companies" (not "Experienced legal services")',
            },
        },
        "subheadline": {
            "goal": "Expand on the headline with one sentence of concrete value",
            "constraints": "Max 120 characters, specific benefit not feature",
            "examples": {
                "creative_agency": '"From brand strategy to pixel-perfect execution—we make your vision unforgettable"',
                "saas": '"Deploy production-ready infrastructure in minutes, not months"',
                "legal_finance": '"Proven track record: $2B recovered for clients across complex litigation"',
            },
        },
        "service": {
            "goal": "Rewrite service name to be descriptive and benefit-driven",
            "constraints": "2-4 words, action-oriented when possible",
            "examples": {
                "creative_agency": '"Brand Identity → Brand Architecture & Strategy"',
                "saas": '"Dashboard → Real-Time Analytics Command Center"',
                "legal_finance": '"Corporate Law → M&A and Corporate Transactions"',
            },
        },
        "cta": {
            "goal": "Create a compelling call-to-action that drives conversion",
            "constraints": "2-4 words, action verb, relevant to context",
            "examples": {
                "creative_agency": '"View Our Work", "Start a Project", "See Case Studies"',
                "saas": '"Start Free Trial", "Book a Demo", "Get Started Free"',
                "legal_finance": '"Schedule Consultation", "Discuss Your Case", "Contact Our Team"',
            },
        },
        "body": {
            "goal": "Rewrite body copy to be concise, impactful, and scannable",
            "constraints": "Cut by 40%, keep only essential points, use bullet points",
            "examples": {
                "creative_agency": 'Before: "We have over 10 years of experience..." After: "A decade shipping award-winning work for startups to Fortune 500s"',
                "saas": 'Before: "Our solution provides..." After: "Get real-time insights. Deploy in 5 minutes. Scale to millions."',
                "legal_finance": 'Before: "Our attorneys are highly qualified..." After: "25 attorneys. 150+ years combined experience. $1B+ recovered."',
            },
        },
    }

    spec = content_type_specs.get(content_type, content_type_specs["body"])
    example = spec["examples"].get(industry, "")

    prompt = f"""You are a premium copywriter rewriting content for a {industry} website.

# CONTENT REWRITE INSTRUCTIONS
{design_config["content_rewrite_instructions"]}

# SPECIFIC TASK: {content_type.upper()}
Goal: {spec["goal"]}
Constraints: {spec["constraints"]}
{f"Example for {industry}: {example}" if example else ""}

# ORIGINAL CONTENT
"{original_content}"

# CONTEXT
Company: {company_name}
Brand Tone: {brand_tone}
Industry: {industry}

# YOUR TASK
Rewrite the content following the instructions above. Return ONLY the rewritten content, nothing else.
Make it 2x more impactful. Cut everything that doesn't serve the core message.
"""

    return prompt
