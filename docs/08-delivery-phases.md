# Delivery Phases

## Phase 0: Product Definition

Goal:

- lock the system vision, data relationships, and quality rules before implementation

Deliverables:

- product scope
- system architecture
- data model
- auth model
- analytics model
- route map
- extraction policy
- generation policy
- design variability rules
- frontend page map
- API resource map
- brand asset provenance rules
- review rubric for generated previews
- palette mode strategy for zinc, light, and colorful outputs
- placeholder-free production policy

Exit criteria:

- every major feature has a backend and frontend owner
- every persisted object has a clear purpose
- the system has a clear answer for how it turns a source site into a brief, then a brief into a preview
- the team agrees on the source-to-preview traceability standard
- the design review loop is defined before implementation starts
- the system knows when to preserve the source site's visual tone versus when to reinterpret it
- the team agrees that missing data becomes an admin-visible gap, never a placeholder

## Phase 1: Internal Shell

Goal:

- create the secure admin shell and data foundation

Deliverables:

- Next.js admin app
- Tailwind and shadcn/ui base design system
- backend service skeleton
- MongoDB connection and collections
- email allowlist auth
- session handling
- empty dashboard and navigation
- shared API client and typed resource wrappers
- route guards for admin-only surfaces
- shell states for loading, empty, error, and unauthorized views

Exit criteria:

- approved users can log in
- unauthorized users are blocked
- admin routes are protected
- the shell can render stub data from the planned API shapes
- the main navigation matches the documented route map

## Phase 2: Lead Intake

Goal:

- allow CSV uploads and manual lead creation

Deliverables:

- CSV parser
- bulk import workflow
- URL normalization
- lead list screen
- lead detail screen
- job creation on import
- `/api/leads` create/list/detail endpoints
- `/api/leads/import` bulk import endpoint
- `/api/jobs/:id` job status endpoint
- lead row, detail drawer, and import progress UI
- duplicate detection and merge prompts

Exit criteria:

- a batch of leads appears in the admin
- each lead has a clear status
- imported rows resolve to a lead record, a job record, and a visible frontend state
- the lead list can render from the real list endpoint without mock-only fields

## Phase 3: Discovery and Extraction

Goal:

- find websites, crawl public pages, and produce structured content

Deliverables:

- website detection
- sitemap discovery
- public content crawling
- extraction summaries
- crawl error states
- extraction review UI
- source citations
- confidence scores
- page inventory
- `/api/leads/:id/extraction` snapshot endpoint
- `/api/leads/:id/pages` discovered page inventory endpoint
- `/api/jobs/:id` crawl progress endpoint
- page-level citations and confidence badges in the UI
- brand asset capture for logo, color, image, and typography cues

Exit criteria:

- a lead detail page shows real extracted structure
- crawl progress is visible
- the admin can inspect the source material that led to the generated brief
- extracted facts are traceable to pages or assets
- missing or low-confidence source signals are visible rather than hidden

## Phase 4: Briefing and Review

Goal:

- convert extracted website intelligence into a structured, reviewable brief

Deliverables:

- site brief generation
- inferred audience and tone profile
- conversion angle recommendation
- source-to-brief traceability
- brief approval workflow
- `/api/leads/:id/brief` read and update endpoints
- brief versioning and approval states
- editable review form with locked source citations
- confidence and inference labels on every recommendation

Exit criteria:

- each lead has a clear interpreted brief before visual generation begins
- operators can edit or approve the brief without losing traceability
- the frontend can display source-backed and inferred brief fields side by side
- approved briefs are persisted as versioned records, not overwritten drafts

## Phase 5: Design Generation

Goal:

- turn extracted data into premium redesign output

Deliverables:

- brand token extraction
- hero variant selection
- section generation
- CTA strategy generation
- preview site rendering
- version history
- theme library selection
- quality score
- before/after comparison
- `/api/sites/:id` generated site detail endpoint
- `/api/sites/:id/versions` version history endpoint
- `/api/themes` theme library endpoint
- `/api/sites/:id/compare` source-to-preview comparison payload
- deployed preview URL or preview slug for browser-based review
- review agent pass/fail rubric
- screenshot-based visual QA against the deployed preview
- brand application using extracted logo, image, color, and typography cues
- explicit palette mode selection based on extracted visual cues
- placeholder-free preview policy
- structured override model for manual edits
- edit workspace for operator changes
- export snapshot and handoff metadata

Exit criteria:

- each lead can produce a preview site
- previews look branded and distinct
- generated outputs are not visually repetitive across a batch
- the review agent can inspect the live preview in a browser, capture screenshots, and flag design issues
- brand tokens used in the preview can be traced back to extracted source assets or explicitly marked inferences
- the selected visual mode is explainable from the source website's own design language
- no public-facing preview contains lorem ipsum, fake metrics, stock filler, or invented brand claims
- approved edits survive regeneration and are visible as durable overrides

## Phase 5.5: Operator Edit Loop

Goal:

- let the operator refine the generated site before the meeting or before sending a message

Deliverables:

- structured override editor
- before/after diff views
- regenerate-from-overrides action
- disable/revert override controls
- export bundle or snapshot creation
- GitHub or local handoff status

Exit criteria:

- operator changes are stored as overrides, not lost in regenerated output
- regenerated previews respect approved edits
- export artifacts can be created without changing the canonical site spec
- the preview and the exported handoff stay traceable to the same lead and version

## Phase 6: Outreach Preparation

Goal:

- generate message drafts that align with the redesign

Deliverables:

- channel-specific message drafts
- tone controls
- CTA references
- Calendly link integration fields
- copy review UI
- `/api/messages` draft endpoints
- status states for draft, edited, and ready
- preview-link insertion from the generated site record
- export-link insertion if a handoff bundle has been created

Exit criteria:

- admin can copy a message draft for outreach
- message copy matches the preview story
- the message draft reads from the approved brief and generated site data, not from separate ad hoc text

## Phase 7: Analytics

Goal:

- measure whether generated sites are being visited and acted on

Deliverables:

- preview event instrumentation
- analytics ingestion endpoint
- analytics dashboard
- lead-to-visit tracking
- CTA click tracking
- `/api/analytics/events` ingestion endpoint
- `/api/analytics/dashboard` aggregate endpoint
- `/api/analytics/sites/:id` site metrics endpoint
- `/api/analytics/leads/:id` lead funnel endpoint
- event payloads that map cleanly to the admin charts and tables

Exit criteria:

- admin can see visits and clicks by site and lead
- the dashboard renders from aggregate analytics data rather than fabricated counts
- all tracked events have an explicit consumer in the admin UI

## Phase 8: Scale, QA, and Automation Readiness

Goal:

- prepare for high-volume lead processing and future outbound automation

Deliverables:

- retry logic
- queue health reporting
- batching controls
- source attribution
- exportable campaign records
- quality review queues
- regeneration controls
- theme diversity checks
- palette diversity checks
- automation handoff records
- browser-based preview audit workflow
- visual regression review checklist
- screenshot storage and review metadata
- operator controls for regenerating a site after QA fails
- final approval state for publish-ready previews
- production-readiness gate for missing-field review

Exit criteria:

- system can handle bulk imports safely
- future sender automation can consume the prepared data
- operators can review, regenerate, and export at scale without breaking traceability
- the review process can block a preview until design, brand, and content checks pass
- every publishable site has a documented review outcome and screenshot-backed signoff
- every publishable site has a documented palette choice and rationale tied to extracted source cues
- every publishable site has no unresolved placeholder risks or unreviewed gaps

## Implementation Order Recommendation

1. Auth and shell
2. Lead intake
3. Discovery and extraction
4. Briefing and review
5. Generation, preview rendering, and design QA
6. Messaging drafts
7. Analytics
8. Scale hardening
