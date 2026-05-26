# Content Extraction and Site Brief

## Purpose

Turn a public website into a structured, reviewable, traceable brief that can drive redesign generation.

This layer sits between raw crawl data and the generated site.

## Input Sources

Only public sources should be used by default:

- homepage HTML
- public internal pages
- sitemap.xml or sitemap index files
- public metadata
- public image and logo assets
- public social/profile links if exposed on the site

The system should not depend on hidden, authenticated, or private content.

## Crawl Order

Recommended order:

1. Resolve canonical domain.
2. Check for sitemap files.
3. Crawl homepage and top-level navigation targets.
4. Expand into sitemap-discovered pages.
5. Prioritize pages that contain about, services, pricing, contact, case studies, or product information.
6. Normalize and summarize what was found.

## Extraction Targets

The extractor should capture:

- company name and canonical website
- page inventory
- services or products
- positioning and value proposition
- audience clues
- CTA patterns
- trust signals
- tone and writing style
- visual direction cues
- brand colors and logo assets
- image style cues and media references
- metadata and social cards
- content gaps
- obvious conversion friction
- unresolved gaps that block production-ready generation

## Site Brief Output

The output should be a `site_brief` object that includes:

- company summary
- inferred audience hypothesis
- value proposition summary
- tone profile
- conversion angle
- recommended hero direction
- recommended section stack
- proof points
- source citations
- confidence score
- reviewer notes
- brief version
- brand asset provenance
- inferred-vs-source-backed field labels
- missing-field markers for admin review

## Traceability Rules

Every non-trivial recommendation should be traceable to either:

- a source page
- a sitemap path
- a visible asset
- or an explicitly marked inference

If the system infers something, it should label it as an inference and assign a confidence level.

## Quality Rules

- Do not invent services, testimonials, logos, or client claims.
- Do not rely on placeholder copy when source material is available.
- If the public site is sparse, generate a stronger strategic brief instead of pretending certainty.
- If multiple pages conflict, preserve the conflict and surface it in review.
- If a design recommendation depends on a visual cue, record which source asset or page established it.
- If a required field is missing, expose it as a gap instead of substituting a placeholder.

## Admin Review Surface

The admin should let operators inspect:

- the source pages that were crawled
- extracted page summaries
- citations backing the brief
- missing or low-confidence fields
- the final recommended conversion angle
- the list of unresolved items preventing a production-ready preview

Operator overrides:
- Operators can save structured overrides (via the `/api/sites/:id/overrides` endpoint) to make targeted adjustments to the generated preview. A `themeKey` override tells the generator to prefer the chosen theme on the next generation pass; the generator will record the reason and persist the theme selection on the site record so the workspace shows the active operator theme.

## Useful Extensions

Later versions can add:

- comparison against competitor sites
- extraction of industry keywords from public positioning
- language detection and localization hints
- structured FAQ extraction
- public review and testimonial parsing
