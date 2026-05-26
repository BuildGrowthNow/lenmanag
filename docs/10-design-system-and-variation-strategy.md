# Design System and Variation Strategy

## Purpose

Define how the platform generates websites that feel bespoke, premium, and conversion-oriented without falling into the same layout every time.

## Core Principle

Use one shared Next.js rendering engine with many generated site configurations.

Do not build one separate application per lead.

Instead:

- keep a single renderer
- store design decisions as data
- select from reusable theme families
- vary layout, typography, motion, and section order per site

## Design Goals

Every generated site should:

- feel clearly more premium than the source site
- preserve the company's recognizable brand signals
- adapt to the company's audience and industry
- emphasize conversion without looking like a generic sales page
- remain usable on desktop and mobile
- match the extracted site's visual language enough that the output feels intentionally related, not randomly themed

## Theme Library

The generator should choose from a library of reusable theme families.

Each theme family should define:

- hero structure
- section stack
- typography pairing
- spacing density
- color treatment
- motion preset
- CTA style
- image treatment
- palette mode

Theme families can be optimized for different goals such as:

- agency or studio storytelling
- B2B service conversion
- local service lead generation
- premium product positioning
- founder-led personal brand sites

Palette mode should be an explicit design decision, not an accident.

Recommended modes:

- `zinc` for restrained, editorial, or low-color brands
- `light` for airy, clean, minimalist, or high-clarity brands
- `colorful` for expressive, saturated, playful, or high-energy brands

The palette mode should be selected from extracted signals such as:

- source palette saturation and contrast
- logo color behavior
- image treatment and background usage
- typography mood
- overall site density and visual energy

If the source site is strongly monochrome, the generated site should usually remain in a zinc or light family.
If the source site is bright, layered, or colorful, the generated site should be allowed to carry that energy forward without flattening it.

## Variation Rules

The system should avoid repeated output in bulk runs.

Recommended rules:

- do not reuse the same hero family for every site in a batch
- vary the first two sections when the source content allows it
- vary motion intensity by site and industry
- vary visual density and editorial rhythm
- vary CTA placement based on the conversion angle

If two generated sites are for similar businesses, the generator should still produce different compositions, different section ordering, or a different visual tone.

## Brand Adaptation

Brand adaptation should use:

- source site colors
- source site logo or wordmark
- visible typography cues
- image style cues
- writing tone cues
- audience cues
- existing visual mode cues such as zinc, light, or colorful presentation

If the source site has weak branding, the system should infer a brand direction from the business category and audience, but mark that direction as inferred.

The generated site should visibly reuse the source brand's:

- logo or wordmark asset when available
- dominant and accent colors when usable
- image treatment and cropping style
- typography mood and hierarchy cues
- spacing and density preferences when they are part of the brand identity
- overall palette mode and contrast style when they are clearly signaled by the source

## Override Policy

Manual operator changes should not be treated as temporary hacks.

If an operator changes copy, layout, CTA order, or styling, the system should:

- store the change as a structured override
- preserve the original generated value for comparison
- reapply the override on regeneration
- show the override clearly in review and export views

Overrides should win over generated defaults unless the override conflicts with a hard quality or safety rule.

## Hero Strategy

Heroes should be treated as the main differentiator.

Good hero options might include:

- bold editorial headline with proof stack
- split narrative with product and trust panel
- immersive visual hero with layered CTAs
- conversion-first hero with scannable benefits
- cinematic or motion-led hero inspired by high-end interactive web patterns

The goal is not to copy reference sites directly.
The goal is to use them as a quality bar for interaction, pacing, and presentation.

## Section Strategy

The section stack should be generated from the brief rather than fixed globally.

Possible sections include:

- benefits
- services
- process
- proof
- testimonials
- case studies
- pricing or starting point
- FAQ
- contact and CTA

## Quality Gates

Before a preview is marked ready, the system should check that:

- the design uses source-derived brand cues
- the content is grounded in public information
- the content contains no placeholder copy, fake metrics, or stock testimonials
- the layout is not a near-clone of another generated site
- the CTA strategy matches the business model
- the preview remains readable on mobile
- the deployed preview passes screenshot-based review against the source website and brief
- the review notes clearly separate source-backed decisions from inferred design choices
- the logo, images, and color usage are visually consistent with the extracted brand package
- the selected palette mode matches the extracted site's design decisions closely enough to feel intentional
- approved overrides are preserved after regeneration and can be inspected in diff form

## Review Surface

Operators should be able to inspect:

- chosen theme family
- selected hero variant
- section sequence
- design rationale
- quality score
- source comparison
- screenshot comparison
- review notes
- brand token provenance

## Future Extensions

Later versions can add:

- auto-generated page templates beyond the landing page
- per-industry motion packs
- design benchmark scoring against premium reference sites
- batch-level diversity scoring
- automatic image style synthesis
