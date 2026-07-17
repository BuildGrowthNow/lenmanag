# Creative Design Upgrade: 3-Phase Implementation Guide

**Goal**: Transform generated landing pages from generic templates to Awwwards-level creative designs with real wow factor.

**Problem Summary**: Current outputs feel like simple templates with basic heroes, minimal interactivity, no animations, and no creative risk-taking. The constraint is two-fold:
1. The **Master Brief** doesn't ask for creative direction — it's strategic but not artistic
2. The **TSX Generation Prompt** is defensive (70% "DO NOT" rules) and prescriptive (rigid template structure)

---

## Phase 1: Enrich the Master Brief with Creative Direction

**Files to modify:**
- `apps/backend/app/schemas/brief.py` — Add new schema fields
- `apps/backend/app/core/master_brief.py` — Update LLM prompt
- `apps/web/src/lib/types.ts` — Add TypeScript types
- `apps/web/src/components/lead-brief-review.tsx` — Display new fields
- `apps/web/src/app/app/leads/[id]/brief/brief-review-client.tsx` — Display new fields

### 1.1 Update Backend Schema (`apps/backend/app/schemas/brief.py`)

Add a new `CreativeDirection` model and integrate it into `MasterBrief`:

```python
# Add after line 117 (after BrandAssets class)

class CreativeDirection(BaseModel):
    """Art direction block for the landing page design"""

    designConcept: str = Field(
        ...,
        description="One-sentence creative concept (e.g., 'Floating glass cards emerging from a dark cosmos')"
    )
    heroTreatment: str = Field(
        ...,
        description="Specific hero approach (e.g., 'Split-screen with looping video left, kinetic typography right')"
    )
    signatureTechnique: str = Field(
        ...,
        description="One memorable effect that makes this site stand out (e.g., 'Cursor-following gradient orb', 'Morphing blob background')"
    )
    layoutStrategy: str = Field(
        ...,
        description="Grid philosophy (e.g., 'Asymmetric bento grid, no full-width sections except hero', 'Alternating split-screen reveals')"
    )
    scrollBehavior: str = Field(
        default="smooth-reveal",
        description="How the page responds to scroll (e.g., 'parallax-layers', 'snap-sections', 'smooth-reveal', 'horizontal-scroll-section')"
    )
    microInteractions: list[str] = Field(
        default_factory=list,
        description="Specific hover/click/scroll micro-interactions (e.g., 'hover card tilt', 'button magnetic pull', 'text reveal on scroll')"
    )
    colorMood: str = Field(
        ...,
        description="Emotional color direction (e.g., 'Dark mode with electric accents', 'Warm gradients fading to white', 'Monochrome with one pop color')"
    )
    typographyPersonality: str = Field(
        ...,
        description="Type treatment (e.g., 'Oversized display headings with tight tracking', 'Mixed serif/sans contrast', 'Kinetic text animations')"
    )
    inspirationKeywords: list[str] = Field(
        default_factory=list,
        description="Design vocabulary (e.g., 'editorial', 'brutalist', 'glassmorphism', '3D depth', 'organic shapes', 'geometric precision')"
    )
    avoidPatterns: list[str] = Field(
        default_factory=list,
        description="What NOT to do for this brand (e.g., 'generic stock photo grids', 'centered everything', 'safe corporate blue')"
    )
```

Then update the `MasterBrief` class to include it (after line 170, in the Creative Direction section):

```python
    # Creative Direction (enhanced)
    visualStyle: str = Field(
        ..., description="Description of look/feel (minimal, bold, playful, etc)"
    )
    colorStrategy: str = Field(
        ..., description="How colors should be used (dark+neon, soft pastels, etc)"
    )
    motionLevel: Literal["none", "subtle", "moderate", "dramatic"] = Field(
        ..., description="Animation intensity"
    )
    specialEffects: list[str] = Field(
        default_factory=list, description="3d-hero, parallax-scroll, particle-bg, etc"
    )
    creativeDirection: CreativeDirection = Field(
        default_factory=CreativeDirection,
        description="Detailed art direction for the page design"
    )
```

Also add a default factory for CreativeDirection:

```python
# Update the CreativeDirection class to have proper defaults for factory
class CreativeDirection(BaseModel):
    """Art direction block for the landing page design"""

    designConcept: str = Field(
        default="Modern and engaging",
        description="One-sentence creative concept"
    )
    heroTreatment: str = Field(
        default="Full-width hero with centered content",
        description="Specific hero approach"
    )
    signatureTechnique: str = Field(
        default="Smooth scroll animations",
        description="One memorable effect"
    )
    layoutStrategy: str = Field(
        default="Clean grid layout",
        description="Grid philosophy"
    )
    scrollBehavior: str = Field(
        default="smooth-reveal",
        description="How the page responds to scroll"
    )
    microInteractions: list[str] = Field(
        default_factory=list,
        description="Specific hover/click/scroll micro-interactions"
    )
    colorMood: str = Field(
        default="Professional with brand accents",
        description="Emotional color direction"
    )
    typographyPersonality: str = Field(
        default="Clean sans-serif with clear hierarchy",
        description="Type treatment"
    )
    inspirationKeywords: list[str] = Field(
        default_factory=list,
        description="Design vocabulary"
    )
    avoidPatterns: list[str] = Field(
        default_factory=list,
        description="What NOT to do"
    )
```

### 1.2 Update Master Brief Generation Prompt (`apps/backend/app/core/master_brief.py`)

Replace the `_build_initial_prompt` function (starting at line 164) with this enhanced version:

```python
def _build_initial_prompt(extraction_summary: str) -> str:
    """Build the initial master brief generation prompt."""
    prompt = f"""You are an award-winning creative director designing a landing page. Your goal is to create something that would win an Awwwards Site of the Day — not a template, but a memorable experience.

IMPORTANT: This data has been pre-analyzed by AI. The services, tone, and audience descriptions are already synthesized — use them as-is, don't re-interpret them.

{extraction_summary}

## Your Mission

Create a landing page brief that:
1. Has a SIGNATURE MOMENT — one thing visitors will remember
2. Breaks at least one "safe" convention (centered layouts, stock grids, generic heroes)
3. Uses motion and interactivity as design tools, not decorations
4. Matches the brand's personality while pushing creative boundaries

## Design Vocabulary (use these concepts)

**Hero Treatments** (pick one, be specific):
- Split-screen with video/animation on one side
- Oversized kinetic typography that responds to scroll
- 3D object or scene that rotates/morphs
- Full-bleed image with text reveal on scroll
- Bento grid hero with multiple interactive cards
- Ambient gradient mesh or particle background

**Layout Strategies** (break the mold):
- Asymmetric bento grids (varied card sizes, not uniform)
- Horizontal scroll sections for galleries/features
- Alternating full-bleed and contained sections
- Sticky sidebars with scrolling content
- Overlapping elements and negative space
- Magazine/editorial layouts with mixed media

**Micro-interactions** (make it feel alive):
- Magnetic buttons that pull toward cursor
- Cards that tilt on hover (3D transform)
- Text that reveals character-by-character
- Parallax depth layers (foreground/background move differently)
- Scroll-triggered reveals (fade up, slide in, scale)
- Cursor effects (custom cursor, trailing elements, glow)

**Typography Treatments**:
- Oversized display text (100px+) with tight letter-spacing
- Mixed serif/sans-serif for contrast
- Animated text (typewriter, morphing, bouncing)
- Variable font weight animations
- Text masks revealing images/videos

## Constraints
- This is a SINGLE landing page (not a multi-page site)
- Keep content concise — headlines under 8 words, descriptions under 2 sentences
- The page must have a clear conversion goal
- Choose 4-7 sections maximum
- Every field must have real content, no placeholders
- Match the brand's industry and audience while being creative

## Output Format

Return a JSON object with this structure:
{{
  "businessGoal": "What this landing page should achieve",
  "primaryAudience": "Who we're talking to",
  "conversionAction": "The one thing we want them to do",
  "valueProposition": "Why they should care (1-2 sentences)",
  "toneAndVoice": "How we sound (e.g., 'confident and direct, not corporate-speak')",
  "visualStyle": "Overall aesthetic (be specific, not 'clean and modern')",
  "colorStrategy": "How colors create mood (e.g., 'dark canvas with electric blue accents for tech authority')",
  "motionLevel": "none|subtle|moderate|dramatic",
  "specialEffects": ["parallax-scroll", "3d-hero", "particle-bg", "cursor-glow", "morphing-shapes"],
  "creativeDirection": {{
    "designConcept": "One sentence capturing the creative vision (e.g., 'A dark command center where data comes alive')",
    "heroTreatment": "Specific hero design (e.g., 'Split-screen: left side has looping product video, right side has oversized headline with scroll-triggered subtext reveal')",
    "signatureTechnique": "The ONE thing that makes this site memorable (e.g., 'Floating 3D product that follows cursor movement')",
    "layoutStrategy": "How sections are arranged (e.g., 'Asymmetric bento grid for features, full-bleed testimonial, sticky pricing sidebar')",
    "scrollBehavior": "parallax-layers|snap-sections|smooth-reveal|horizontal-scroll-section",
    "microInteractions": ["button magnetic pull", "card 3D tilt on hover", "text fade-up on scroll", "cursor trailing gradient"],
    "colorMood": "Emotional color story (e.g., 'Deep charcoal base with warm amber accents — feels premium but approachable')",
    "typographyPersonality": "How type creates personality (e.g., 'Massive 120px headlines in a geometric sans, body in a warm serif')",
    "inspirationKeywords": ["editorial", "dark-mode", "glassmorphism", "depth", "kinetic"],
    "avoidPatterns": ["centered-everything", "generic-icon-grid", "stock-photo-hero", "blue-gradient-cta"]
  }},
  "headline": "Main hero headline (8 words max, compelling)",
  "subheadline": "Supporting line (2 sentences max)",
  "sections": [
    {{
      "purpose": "social-proof|services|process|cta|about|features|pricing|faq|gallery|testimonials",
      "headline": "Section headline (clear, specific)",
      "contentSummary": "What goes in this section (detailed)",
      "suggestedApproach": "Specific component approach (e.g., 'Bento grid with 3 large + 2 small cards, hover reveals detail overlay')",
      "contentPoints": ["specific point 1", "specific point 2", "specific point 3"]
    }}
  ],
  "ctaStrategy": "How CTAs work across the page (e.g., 'Sticky header CTA + mid-page floating CTA + footer full-width CTA bar')",
  "aiReasoning": "Why these creative choices fit this brand and audience",
  "confidenceScore": 85
}}

CRITICAL: 
- Every field must be populated with real, specific content
- The creativeDirection must have SPECIFIC techniques, not generic descriptions
- suggestedApproach for each section should describe a specific component pattern
- Think like an Awwwards judge — what makes this site worth featuring?

Return ONLY valid JSON, no markdown formatting."""

    return prompt
```

Also update `_build_refinement_prompt` (starting at line 215) to include creativeDirection in the previous summary and output format.

### 1.3 Update `_build_master_brief_from_response` function

In `apps/backend/app/core/master_brief.py`, update the function starting at line 279 to handle the new creativeDirection field:

```python
# After building sections (around line 346), add:

    # Build creative direction
    creative_data = brief_data.get("creativeDirection", {})
    creative_direction = CreativeDirection(
        designConcept=creative_data.get("designConcept", "Modern and engaging"),
        heroTreatment=creative_data.get("heroTreatment", "Full-width hero with centered content"),
        signatureTechnique=creative_data.get("signatureTechnique", "Smooth scroll animations"),
        layoutStrategy=creative_data.get("layoutStrategy", "Clean grid layout"),
        scrollBehavior=creative_data.get("scrollBehavior", "smooth-reveal"),
        microInteractions=creative_data.get("microInteractions", []),
        colorMood=creative_data.get("colorMood", "Professional with brand accents"),
        typographyPersonality=creative_data.get("typographyPersonality", "Clean sans-serif with clear hierarchy"),
        inspirationKeywords=creative_data.get("inspirationKeywords", []),
        avoidPatterns=creative_data.get("avoidPatterns", []),
    )
```

Then add `creativeDirection=creative_direction,` to the MasterBrief constructor (around line 365).

### 1.4 Update Frontend Types (`apps/web/src/lib/types.ts`)

Add after line 1137 (after `MasterBriefSection` type):

```typescript
export type CreativeDirection = {
  designConcept: string;
  heroTreatment: string;
  signatureTechnique: string;
  layoutStrategy: string;
  scrollBehavior: string;
  microInteractions: string[];
  colorMood: string;
  typographyPersonality: string;
  inspirationKeywords: string[];
  avoidPatterns: string[];
};
```

Then update the `MasterBrief` type (around line 1139) to include:

```typescript
export type MasterBrief = {
  // ... existing fields ...
  creativeDirection?: CreativeDirection;
  // ... rest of fields ...
};
```

### 1.5 Update Frontend Display Components

#### `apps/web/src/components/lead-brief-review.tsx`

Add a new section to display creative direction (after the "Page Sections" section around line 244):

```tsx
{brief.creativeDirection && (
  <div className="space-y-3">
    <div className="text-xs uppercase tracking-[0.18em] text-muted font-semibold">Creative Direction</div>
    <div className="grid gap-3 md:grid-cols-2">
      <div className="rounded-2xl border border-line bg-panel-2 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Design Concept</div>
        <div className="mt-2 text-sm text-text">{brief.creativeDirection.designConcept}</div>
      </div>
      <div className="rounded-2xl border border-line bg-panel-2 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Hero Treatment</div>
        <div className="mt-2 text-sm text-text">{brief.creativeDirection.heroTreatment}</div>
      </div>
      <div className="rounded-2xl border border-line bg-panel-2 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Signature Technique</div>
        <div className="mt-2 text-sm text-text font-medium">{brief.creativeDirection.signatureTechnique}</div>
      </div>
      <div className="rounded-2xl border border-line bg-panel-2 p-4">
        <div className="text-xs uppercase tracking-[0.18em] text-muted">Layout Strategy</div>
        <div className="mt-2 text-sm text-text">{brief.creativeDirection.layoutStrategy}</div>
      </div>
      {brief.creativeDirection.microInteractions.length > 0 && (
        <div className="rounded-2xl border border-line bg-panel-2 p-4 md:col-span-2">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Micro-interactions</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {brief.creativeDirection.microInteractions.map((interaction, i) => (
              <span key={i} className="text-xs px-2 py-1 bg-panel-3 rounded-full text-text">{interaction}</span>
            ))}
          </div>
        </div>
      )}
      {brief.creativeDirection.inspirationKeywords.length > 0 && (
        <div className="rounded-2xl border border-line bg-panel-2 p-4 md:col-span-2">
          <div className="text-xs uppercase tracking-[0.18em] text-muted">Inspiration Keywords</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {brief.creativeDirection.inspirationKeywords.map((keyword, i) => (
              <span key={i} className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded-full">{keyword}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  </div>
)}
```

#### `apps/web/src/app/app/leads/[id]/brief/brief-review-client.tsx`

Add similar display in the "Creative Direction" section (around line 208). Replace the existing Creative Direction section with:

```tsx
{/* Creative Direction */}
<div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-4">
  <h2 className="text-lg font-semibold text-zinc-300">Creative Direction</h2>
  
  {/* Core creative vision */}
  {brief.creativeDirection && (
    <div className="space-y-4">
      <div className="p-4 bg-gradient-to-r from-blue-950/30 to-purple-950/30 border border-blue-900/30 rounded-lg">
        <h3 className="text-sm text-blue-400 mb-1">Design Concept</h3>
        <p className="text-sm font-medium">{brief.creativeDirection.designConcept}</p>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Hero Treatment</h3>
          <p className="text-sm">{brief.creativeDirection.heroTreatment}</p>
        </div>
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Signature Technique</h3>
          <p className="text-sm text-blue-400">{brief.creativeDirection.signatureTechnique}</p>
        </div>
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Layout Strategy</h3>
          <p className="text-sm">{brief.creativeDirection.layoutStrategy}</p>
        </div>
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Scroll Behavior</h3>
          <p className="text-sm">{brief.creativeDirection.scrollBehavior}</p>
        </div>
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Color Mood</h3>
          <p className="text-sm">{brief.creativeDirection.colorMood}</p>
        </div>
        <div>
          <h3 className="text-sm text-zinc-500 mb-1">Typography</h3>
          <p className="text-sm">{brief.creativeDirection.typographyPersonality}</p>
        </div>
      </div>

      {brief.creativeDirection.microInteractions.length > 0 && (
        <div>
          <h3 className="text-sm text-zinc-500 mb-2">Micro-interactions</h3>
          <div className="flex flex-wrap gap-2">
            {brief.creativeDirection.microInteractions.map((item) => (
              <span key={item} className="text-xs px-2 py-1 bg-green-900/30 text-green-400 rounded">
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {brief.creativeDirection.inspirationKeywords.length > 0 && (
        <div>
          <h3 className="text-sm text-zinc-500 mb-2">Inspiration Keywords</h3>
          <div className="flex flex-wrap gap-2">
            {brief.creativeDirection.inspirationKeywords.map((keyword) => (
              <span key={keyword} className="text-xs px-2 py-1 bg-purple-900/30 text-purple-400 rounded">
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {brief.creativeDirection.avoidPatterns.length > 0 && (
        <div>
          <h3 className="text-sm text-zinc-500 mb-2">Avoid These Patterns</h3>
          <div className="flex flex-wrap gap-2">
            {brief.creativeDirection.avoidPatterns.map((pattern) => (
              <span key={pattern} className="text-xs px-2 py-1 bg-red-900/30 text-red-400 rounded line-through">
                {pattern}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )}

  {/* Legacy fields for backwards compatibility */}
  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-zinc-800">
    <div>
      <h3 className="text-sm text-zinc-500 mb-1">Visual Style</h3>
      <p className="text-sm">{brief.visualStyle}</p>
    </div>
    <div>
      <h3 className="text-sm text-zinc-500 mb-1">Color Strategy</h3>
      <p className="text-sm">{brief.colorStrategy}</p>
    </div>
    <div>
      <h3 className="text-sm text-zinc-500 mb-1">Motion Level</h3>
      <p className="text-sm">{motionLabel}</p>
    </div>
    <div>
      <h3 className="text-sm text-zinc-500 mb-1">CTA Strategy</h3>
      <p className="text-sm">{brief.ctaStrategy}</p>
    </div>
  </div>
  
  {brief.specialEffects.length > 0 && (
    <div>
      <h3 className="text-sm text-zinc-500 mb-2">Special Effects</h3>
      <div className="flex flex-wrap gap-2">
        {brief.specialEffects.map((effect) => (
          <span key={effect} className="text-xs px-2 py-1 bg-zinc-800 rounded">
            {effect}
          </span>
        ))}
      </div>
    </div>
  )}
</div>
```

---

## Phase 2: Rewrite the TSX Generation Prompt

**Files to modify:**
- `apps/backend/app/core/ai_site_generation.py` — Complete prompt rewrite

### 2.1 Replace `_build_generation_prompt` function

Replace the entire function starting at line 216 in `apps/backend/app/core/ai_site_generation.py`:

```python
def _build_generation_prompt(
    *,
    master_brief: MasterBrief,
    extraction: ExtractionSnapshot,
) -> str:
    """Build the main generation prompt — leads with inspiration, not restrictions."""
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

    # Build creative direction section
    creative_section = ""
    if hasattr(master_brief, 'creativeDirection') and master_brief.creativeDirection:
        cd = master_brief.creativeDirection
        creative_section = f"""
## Creative Direction (THIS IS YOUR NORTH STAR)

**Design Concept**: {cd.designConcept}
**Hero Treatment**: {cd.heroTreatment}
**Signature Technique**: {cd.signatureTechnique} — THIS is what makes this site memorable. Implement it.
**Layout Strategy**: {cd.layoutStrategy}
**Scroll Behavior**: {cd.scrollBehavior}
**Color Mood**: {cd.colorMood}
**Typography Personality**: {cd.typographyPersonality}

**Micro-interactions to implement**:
{chr(10).join(f"  - {mi}" for mi in cd.microInteractions) if cd.microInteractions else "  - Smooth scroll-triggered reveals"}

**Inspiration keywords**: {', '.join(cd.inspirationKeywords) if cd.inspirationKeywords else 'modern, premium, engaging'}

**AVOID these patterns**: {', '.join(cd.avoidPatterns) if cd.avoidPatterns else 'generic templates, centered-everything'}
"""

    prompt = f"""You are building an Awwwards-worthy landing page. Your goal is to create something memorable — not a template, but an experience.

## YOUR CREATIVE TOOLKIT

You have access to powerful libraries. USE THEM CREATIVELY:

### Animation & Motion
- **framer-motion**: motion.div, useScroll, useTransform, useInView, AnimatePresence, variants, stagger
  - Parallax: `useTransform(scrollYProgress, [0, 1], [0, -200])`
  - Scroll-triggered reveals: `initial={{{{ opacity: 0, y: 50 }}}} whileInView={{{{ opacity: 1, y: 0 }}}}`
  - Stagger children: `transition={{{{ staggerChildren: 0.1 }}}}`
  - Magnetic effect: track mouse position, apply transform toward cursor
  
- **GSAP + ScrollTrigger**: For complex timelines and scroll-driven animations
  - Pin sections while content animates
  - Scrub animations tied to scroll position
  - Split text animations

- **Lenis**: Smooth scrolling that makes the whole page feel premium

### 3D & Visual Effects
- **@react-three/fiber + @react-three/drei**: 3D scenes, floating objects, ambient backgrounds
  - Floating product renders
  - Particle systems
  - Gradient spheres and abstract shapes

### UI Components (FULL shadcn/ui library available)
Import from '@/components/ui/*':
- **Layout**: Card, Separator, AspectRatio, ScrollArea
- **Interactive**: Button, Toggle, ToggleGroup, Tabs, Accordion, Collapsible, Dialog, Sheet, Drawer, DropdownMenu, NavigationMenu, Menubar, ContextMenu
- **Forms**: Input, Textarea, Select, Checkbox, RadioGroup, Switch, Slider, Label, Form
- **Feedback**: Alert, AlertDialog, Toast, Progress, Skeleton
- **Data Display**: Avatar, Badge, Calendar, Table, HoverCard, Tooltip, Popover, Command
- **Navigation**: Breadcrumb, Pagination

### Icons
- **lucide-react**: 1000+ icons — Menu, X, ArrowRight, ArrowUpRight, Check, Star, Phone, Mail, MapPin, Play, Pause, ChevronDown, ExternalLink, etc.

### Carousel
- **embla-carousel-react**: Smooth, accessible carousels

{creative_section}

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
- Special Effects: {", ".join(master_brief.specialEffects) if master_brief.specialEffects else "None specified"}

**Hero**:
- Headline: {master_brief.headline}
- Subheadline: {master_brief.subheadline}

**Page Sections**:
{sections_list}

**CTA Strategy**: {master_brief.ctaStrategy}

{brand_section}

## DESIGN PATTERNS TO CONSIDER

**Hero Patterns**:
- Split-screen: video/3D left, text right (or reversed)
- Oversized kinetic typography with scroll-reveal
- Bento grid hero with multiple interactive cards
- Full-bleed with floating elements and parallax layers
- Gradient mesh or particle background with centered content

**Section Patterns**:
- Bento grids with varied card sizes (not uniform 3-column)
- Alternating image/text with scroll-triggered reveals
- Horizontal scroll galleries for features or testimonials
- Sticky headers with scrolling content
- Cards with 3D tilt on hover (transform: perspective + rotateX/Y)
- Overlapping sections with negative margins

**Micro-interactions**:
- Magnetic buttons: track mouse, apply subtle transform toward cursor
- Card tilt: `transform: perspective(1000px) rotateX(${{tiltY}}deg) rotateY(${{tiltX}}deg)`
- Text reveals: `overflow-hidden` parent with `translateY(100%)` to `translateY(0)` child
- Parallax layers: different `useTransform` multipliers for foreground/background
- Hover state transitions: scale, shadow depth, color shifts

**Typography**:
- Display headlines: `text-6xl md:text-8xl lg:text-9xl font-bold tracking-tight`
- Gradient text: `bg-gradient-to-r from-X to-Y bg-clip-text text-transparent`
- Mixed weights: bold headlines, light body
- Letter-spacing: tight for headlines (-0.02em), normal for body

## OUTPUT REQUIREMENTS

1. Export a single default React component
2. Use TypeScript/TSX with proper types
3. Use Tailwind CSS for styling (including arbitrary values like `text-[120px]`)
4. Mobile responsive: sm:, md:, lg:, xl: breakpoints
5. All content from the brief — NO placeholder text
6. Implement the signature technique from creative direction
7. Match the motion level: "{master_brief.motionLevel}"

## BROWSER-ONLY CONSTRAINTS

This runs in the browser, NOT Node.js:
- NO fs, path, child_process, os, crypto, buffer, stream, net, http, https, url, util imports
- NO __dirname, __filename, process.env, require(), module.exports
- NO eval() or new Function()
- Images: use URLs from brand assets or leave empty — NEVER filesystem paths like ./image.png

## CODE STRUCTURE

```tsx
'use client';

import React, {{ useState, useEffect, useRef, useMemo }} from 'react';
import {{ motion, useScroll, useTransform, useInView, AnimatePresence }} from 'framer-motion';
// Import GSAP if using complex scroll animations
// import gsap from 'gsap';
// import {{ ScrollTrigger }} from 'gsap/ScrollTrigger';
// Import Lenis for smooth scroll
// import Lenis from 'lenis';
// Import shadcn components as needed
import {{ Button }} from '@/components/ui/button';
import {{ Card, CardContent }} from '@/components/ui/card';
// Import Lucide icons as needed
import {{ ArrowRight, Menu, X }} from 'lucide-react';

export default function LandingPage() {{
  // Scroll progress for parallax effects
  const {{ scrollYProgress }} = useScroll();
  
  // Refs for scroll-triggered animations
  const heroRef = useRef(null);
  const isHeroInView = useInView(heroRef, {{ once: true }});

  return (
    <div className="min-h-screen bg-background text-foreground">
      {{/* Your creative, unique implementation */}}
    </div>
  );
}}
```

## OUTPUT

Return ONLY the complete TSX code. No markdown code fences, no explanations.
Start with imports and end with the closing brace of the component.
Make it worthy of Awwwards.
"""

    return prompt
```

### 2.2 Update the correction prompt

Also update `_build_correction_prompt` (line 358) to maintain the creative focus when fixing errors — keep the same structure but add a note to preserve creative intent.

### 2.3 Update validation feedback prompt

Update `_retry_generation_with_validation_feedback` (line 498) to also preserve creative direction context.

---

## Phase 3: Add Design Mode Variation

**Files to modify:**
- `apps/backend/app/schemas/brief.py` — Add designMode field
- `apps/backend/app/core/master_brief.py` — Use designMode in prompt
- `apps/backend/app/core/ai_site_generation.py` — Adjust generation based on mode
- `apps/backend/app/api/leads.py` — Accept designMode parameter
- `apps/web/src/lib/types.ts` — Add TypeScript type
- `apps/web/src/components/lead-brief-review.tsx` — Add mode selector (optional)

### 3.1 Define Design Modes

Add to `apps/backend/app/schemas/brief.py` after line 106:

```python
DesignMode = Literal[
    "editorial",      # Heavy typography, asymmetric layouts, magazine feel
    "immersive",      # Full-bleed hero, parallax, ambient motion, cinematic
    "interactive",    # Lots of hover states, scroll triggers, micro-animations
    "minimalist",     # High contrast, few elements, dramatic whitespace
    "playful",        # Organic shapes, bouncy animations, vibrant colors
    "corporate",      # Professional but not boring — structured with subtle polish
]
```

Add to `MasterBrief` class (around line 170):

```python
    designMode: Optional[Literal["editorial", "immersive", "interactive", "minimalist", "playful", "corporate"]] = Field(
        default=None,
        description="Design mode that influences overall creative direction"
    )
```

### 3.2 Update Master Brief Prompt

In `apps/backend/app/core/master_brief.py`, add design mode guidance to `_build_initial_prompt`:

```python
# Add after the extraction_summary, before the mission section:

design_mode_guidance = ""
# This can be passed as a parameter or randomly selected for variety
# For now, we'll let the AI choose based on brand fit

design_mode_guidance = """
## Design Mode Selection

Based on the brand personality and audience, select ONE design mode that fits best:

- **editorial**: Magazine-inspired layouts, heavy typography focus, asymmetric grids, lots of whitespace, mixed media
- **immersive**: Full-bleed visuals, cinematic parallax, ambient motion, atmospheric backgrounds, story-driven scroll
- **interactive**: Abundant hover states, cursor effects, animated transitions, gamified elements, delightful micro-interactions
- **minimalist**: Dramatic whitespace, bold contrasts, few elements with maximum impact, restrained color palette
- **playful**: Organic shapes, bouncy animations, vibrant colors, unexpected layouts, personality-forward
- **corporate**: Structured grids with subtle polish, professional motion, trust-building design, refined but not boring

Choose the mode in your response under "designMode" — this will guide the code generation phase.
"""
```

Then add `"designMode": "editorial|immersive|interactive|minimalist|playful|corporate"` to the JSON output format.

### 3.3 Use Design Mode in Generation Prompt

In `apps/backend/app/core/ai_site_generation.py`, add design mode-specific guidance:

```python
# Add to _build_generation_prompt, after the creative_section:

design_mode_guidance = ""
if hasattr(master_brief, 'designMode') and master_brief.designMode:
    mode_details = {
        "editorial": """
**EDITORIAL MODE**: Think magazine spread. Heavy typography moments. Asymmetric layouts. 
Mixed font sizes (huge headlines, small captions). Image/text juxtaposition. Generous whitespace.
- Use text-8xl or larger for key headlines
- Mix serif and sans-serif for contrast  
- Consider pull quotes, drop caps, full-bleed images
- Sections should feel like turning pages""",
        
        "immersive": """
**IMMERSIVE MODE**: Think cinematic experience. Full-bleed everything. Parallax depth layers.
Ambient backgrounds (gradients, particles, video). Story-driven scroll progression.
- Use useScroll + useTransform extensively for parallax
- Consider ambient Three.js backgrounds
- Sections should flow like a film, not a document
- Sound/motion cues (even if just visual representations)""",
        
        "interactive": """
**INTERACTIVE MODE**: Make everything respond. Cursor effects. Hover transformations.
Click feedback. Scroll-triggered reveals everywhere. Gamified elements.
- Every card should have a hover state with transform
- Consider magnetic buttons, cursor trails
- Text should reveal on scroll with stagger
- Add micro-celebrations (confetti, pulses, glows)""",
        
        "minimalist": """
**MINIMALIST MODE**: Less is more, but what's there is BOLD. Dramatic whitespace.
Few colors. High contrast. Typography as architecture.
- Limit to 2-3 colors max
- Use scale contrast (tiny vs huge)
- Generous padding and margins
- Let elements breathe — avoid cramped layouts""",
        
        "playful": """
**PLAYFUL MODE**: Personality first. Organic shapes. Bouncy spring animations.
Vibrant colors. Unexpected layouts. Fun > formal.
- Use spring physics in framer-motion
- Consider blob shapes, wavy dividers
- Bright, saturated colors
- Quirky micro-copy and CTAs""",
        
        "corporate": """
**CORPORATE MODE**: Professional polish, not boring. Structured grids with life.
Subtle motion. Trust signals. Refined color usage.
- Clean grid layouts but with visual interest
- Subtle hover states and transitions
- Trust badges, testimonials, social proof prominent
- Motion should feel confident, not flashy""",
    }
    design_mode_guidance = mode_details.get(master_brief.designMode, "")
```

Then include `{design_mode_guidance}` in the prompt after the creative section.

### 3.4 Update Frontend Types

Add to `apps/web/src/lib/types.ts`:

```typescript
export type DesignMode = "editorial" | "immersive" | "interactive" | "minimalist" | "playful" | "corporate";
```

Update `MasterBrief` type:

```typescript
export type MasterBrief = {
  // ... existing fields ...
  designMode?: DesignMode;
  creativeDirection?: CreativeDirection;
  // ... rest of fields ...
};
```

### 3.5 (Optional) Add Mode Selector to Frontend

You can add a mode override in the brief review UI that lets operators force a specific design mode before generation. This is optional but useful for testing.

---

## Testing & Validation

After implementing each phase:

### Phase 1 Testing
1. Run `cd apps/backend && python -m ruff check . && python -m pyright .`
2. Create a new lead and generate a master brief
3. Verify the creativeDirection object appears in the brief
4. Check the frontend displays the new fields

### Phase 2 Testing
1. Run the backend checks
2. Generate a site from an approved brief
3. Check that the generated TSX uses framer-motion, has micro-interactions
4. Verify the code compiles without errors

### Phase 3 Testing
1. Test with different designMode values
2. Verify the generated sites have distinct visual personalities
3. Check that the mode guidance influences the creative direction

---

## Backwards Compatibility

All changes are additive:
- `creativeDirection` has a default factory, so existing briefs without it will work
- `designMode` is optional (defaults to None)
- Frontend conditionally renders new fields only if present
- Generation prompt includes creative direction only if present

No existing data or API contracts are broken.

---

## Summary of Files Changed

| File | Phase | Changes |
|------|-------|---------|
| `apps/backend/app/schemas/brief.py` | 1, 3 | Add CreativeDirection model, designMode field |
| `apps/backend/app/core/master_brief.py` | 1, 3 | Rewrite prompt, parse new fields |
| `apps/backend/app/core/ai_site_generation.py` | 2, 3 | Complete prompt rewrite, design mode guidance |
| `apps/web/src/lib/types.ts` | 1, 3 | Add CreativeDirection, DesignMode types |
| `apps/web/src/components/lead-brief-review.tsx` | 1 | Display creative direction |
| `apps/web/src/app/app/leads/[id]/brief/brief-review-client.tsx` | 1 | Display creative direction |
