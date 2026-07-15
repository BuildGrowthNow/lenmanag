# Backend Specification

## Backend Goals

The Python backend is the brain of the platform.

It should:

- ingest and normalize lead data
- crawl and extract public website content
- identify sitemap URLs
- derive structured business context
- build a site brief from the extracted public context
- generate design-ready site specifications
- store and serve all internal data
- support analytics ingestion and reporting
- enforce internal access rules
- refuse to generate placeholder content when source information is missing
- surface missing data as explicit review items instead of silently substituting filler

## Backend Responsibilities by Layer

### Ingestion Layer

- accept CSV uploads
- accept manual URL submissions
- normalize company and domain records
- deduplicate leads
- enqueue discovery jobs

### Discovery Layer

- resolve website URLs
- inspect sitemap presence
- crawl public pages
- collect metadata and structure
- extract visible content blocks

### Extraction Layer

- parse headings, body copy, navigation, and CTAs
- detect brand colors and logo assets if available
- summarize services, industries, and conversion targets
- produce normalized page summaries
- collect sitemap URLs and page inventories
- attach source citations to extracted facts
- calculate confidence for inferred fields
- record gaps, missing assets, and low-confidence source signals

### Briefing Layer

- convert crawl output into a structured site brief
- infer likely audience and buying motivations
- recommend tone, conversion angle, and hero direction
- preserve traceability between source content and generated recommendations
- preserve missing-field records for admin review

### Generation Layer

- choose hero and section strategies
- map content into premium site structures
- generate design tokens and messaging drafts
- select a theme variant from the design library
- generate rationale for the chosen layout and tone
- build only with real source-derived content, approved inferences, or explicit admin-reviewed fallbacks
- avoid placeholder copy, stock/demo visuals, and fabricated claims

### Override and Export Layer

- accept structured operator edits after preview generation
- merge approved overrides into the rendered site spec
- preserve the original generated version for comparison
- regenerate previews without losing manual changes
- export site snapshots for local work or GitHub handoff
- record export metadata, paths, and commit references

### Serving Layer

- expose lead data to the frontend
- expose preview data to the frontend
- expose analytics summaries to the frontend
- expose job status to the frontend

### Analytics Layer

- receive client-side events from preview sites
- store events in MongoDB
- aggregate event data for reporting

## Job Processing

The backend should support background jobs for:

- website resolution
- sitemap crawl
- page crawl
- content extraction
- design generation
- preview publication
- override application
- export snapshot creation
- analytics aggregation

Each job should report:

- status
- progress
- current step
- error message if any
- timestamps

## Content Extraction Output

The extraction layer should produce structured output like:

- company summary
- product or service list
- core audience hypotheses
- primary and secondary CTAs
- trust signals
- page inventory
- visual cues
- content blocks
- asset references
- source citations
- confidence scores
- sitemap-derived page inventory

## Site Generation Output

The generation layer should produce:

- layout plan
- section stack
- copy blocks
- CTA recommendations
- hero variant
- motion guidance
- brand token mapping
- override merge instructions
- preview slug
- theme variant key
- design rationale
- quality score

## Backend Design Constraints

- Keep raw crawl data separate from interpreted output.
- Keep site briefs separate from generated site documents.
- Keep operator overrides separate from generated site documents, but merge them at render time.
- Keep generation deterministic enough to review and iterate.
- Keep every output traceable back to extracted inputs.
- Keep analytics append-only and query-friendly.
- Keep exported bundles treated as snapshots, not as the source of truth.
- Avoid coupling preview rendering logic directly to crawl logic.
- Prefer public HTML, public metadata, and public assets only.
- Reject or flag any request that depends on hidden, authenticated, or scraped-private content.
- Keep missing source information as explicit gaps rather than filling it with placeholder content.
- Keep public previews free of lorem ipsum, demo images, fake testimonials, invented metrics, and other non-production fillers.

## Error Handling

The backend should preserve useful failure states.

Examples:

- website not found
- sitemap unavailable
- crawl blocked
- logo asset missing
- generation failed
- analytics event malformed
- low-confidence extraction
- conflicting source signals
- theme selection failed
- required content missing
- required brand asset missing
- preview blocked by QA
- source data insufficient for production-ready output
- override conflict detected
- export failed

Those should be visible in the admin with enough detail to act on them.

## Implementation status

**Checklist**

- [x] FastAPI app with modular routers covers auth, leads, jobs, sites, messages, and analytics endpoints (`apps/backend/app/api/*`).
- [x] Core services for ingestion, extraction, briefing, generation, and messaging live in `app/core/*` modules.
- [x] Discovery/extraction/generation jobs run synchronously from API calls; no background worker or queue exists yet - maybe add celery.
- [x] Override/export layers are implemented via the site repository, API endpoints, and UI controls.
- [x] Analytics ingestion + aggregation endpoints are exposed and drive the NSA analytics dashboard.
- [x] Error surfaces exist in code (exceptions, audit logs) but are not fully propagated back to the admin UI.

**Details**

The backend is a solid Phase 1–5 foundation: it authenticates, stores leads, crawls sites, generates briefs/sites, and produces outreach drafts. Celery workers now handle discovery, extraction, and generation jobs off the request thread (with Redis as the default broker and an `CELERY_TASK_ALWAYS_EAGER` escape hatch for tests). The FastAPI routes enqueue work, while the admin UI shows live queue health and job errors via the analytics dashboard. Failed jobs are surfaced as operator-facing alerts so crawl and generation issues never hide behind server logs.
