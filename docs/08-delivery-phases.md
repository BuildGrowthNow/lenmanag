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

### Implementation status

**Checklist**

- [x] Product scope, architecture, data, auth, analytics, and policy docs committed in `/docs` (see `01-product-vision.md`, `02-system-architecture.md`, `03-data-model.md`).
- [x] Backend/frontend ownership and data purpose recorded inside the data model + architecture briefs.
- [ ] Automated traceability matrix linking every persisted field to the brief/extraction/generation pipeline.

**Details**

Phase 0 artifacts live entirely in documentation today and are considered stable enough to guide implementation. The missing work is mostly meta-governance—formalizing how traceability stays enforced as new entities are added.

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

### Implementation status

**Checklist**

- [x] Next.js admin shell with login redirect and protected `/nsa` routes (`apps/web/src/app/page.tsx`, `middleware.ts`).
- [x] Allowlist auth + session cookies served by FastAPI (`apps/backend/app/api/auth.py`).
- [x] Shell states + navigation scaffolding (`components/shell/*`, `components/state/*`).
- [ ] Production-ready secrets and HTTPS cookie settings (currently `secure=False`).

**Details**

The internal shell is functional for trusted operators: the UI loads, auth works against the FastAPI backend, and placeholder panels communicate future work. Hardening session security for deployment (HTTPS-only cookies, secret rotation) remains open.

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

### Implementation status

**Checklist**

- [x] Lead CRUD, CSV import, pagination, filtering APIs (`app/api/leads.py`, `app/api/jobs.py`).
- [x] NSA lead workspace with manual form, CSV upload, job visibility, and pagination (`apps/web/src/app/nsa/leads/page.tsx`).
- [ ] Persistent Mongo storage wired for every lead/job action (local memory fallback still used when Mongo env vars are empty).
- [ ] Duplicate detection UI cues beyond import summaries.

**Details**

Operators can already enter leads manually or upload CSVs, observe job progress, and archive duplicates. The outstanding work is enabling a default Mongo deployment (so job/lead history survives restarts) and surfacing duplicate-merge prompts inline within the list view.

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

### Implementation status

**Checklist**

- [x] Deterministic crawler + brand cue extractor (`core/extraction.py`).
- [x] Extraction/job endpoints on `/leads/{id}/extraction|pages` with audit logging (`app/api/leads.py`).
- [ ] Background worker orchestration & retries (currently synchronous calls only).
- [x] Extraction review UI showing page inventory, citations, and gap list (`apps/web/src/app/nsa/leads/[id]/extraction/page.tsx`, `apps/web/src/components/extraction-review-client.tsx`).

**Details**

The backend can crawl and summarize up to six pages per site, storing citations and cues. Operators can now inspect individual pages, view per-page summaries with citations, see gap lists, and filter pages by status, confidence, and source. Brief approval is gated by critical extraction gaps. Background worker orchestration remains open.

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

### Implementation status

**Checklist**

- [x] Brief create/update/approve endpoints with conflict handling (`app/api/leads.py` + `schemas/brief.py`).
- [x] Back-end evidence model that stores citations and inference labels (`core/sites.py` `_token`, `_brief_evidence`).
- [x] Frontend brief review/editor with locked citations, edit/approval actions, and extraction health gating (`LeadBriefReview`).
- [x] Operator alerts when extraction data is missing, stale, failed, or mid-refresh before edits are allowed.

**Details**

Brief lifecycle logic exists on the server, but the UI still treats briefs as static data surfaced on the site page. A dedicated review workspace (edit form, diff of inferred vs. source-backed fields) is required to officially close Phase 4.

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

### Implementation status

**Checklist**

- [x] Theme library, palette inference, hero/section generation, QA rubric, compare payloads (`core/sites.py`).
- [x] Frontend site workspace showing preview metadata, QA states, compare + version history (`apps/web/src/app/nsa/sites/[id]/page.tsx`).
- [ ] Real preview deployment + screenshot QA tooling (currently conceptual only).
- [x] Export bundle generation and download surface.
- [x] Operator override editor tied to regeneration commands.

**Details**

Backend structures exist for generated sites, versions, QA, and compare responses. Browser-based QA is still blocked on screenshot capture, but operator overrides and export payloads are production-backed: overrides can be created, disabled, and reapplied to regenerations, while exports capture destination metadata and a downloadable bundle history in the UI.

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

### Implementation status

**Checklist**

- [x] Override editor UI/UX.
- [x] Storage model for overrides (schema stubs exist but are unused).
- [ ] Regenerate-from-overrides workflow & diff surfaces.

**Details**

Operators now have a dedicated edit workspace that lists overrides, allows structured creation, and supports disabling individual records while retaining the historical audit trail. Regeneration already replays approved overrides; diff tooling is still open.

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

### Implementation status

**Checklist**

- [x] Message draft repository with lead/brief/site linkage and Calendly detection (`core/messages.py`).
- [x] NSA messages page with per-lead draft summaries and workspace component (`apps/web/src/app/nsa/messages/page.tsx`, `components/message-drafts-workspace`).
- [ ] Tone/CTA controls exposed in the UI for manual tuning.
- [ ] Channel-specific delivery states (WhatsApp, LinkedIn, email) with status transitions.
- [ ] Copy review UI referencing the actual preview rather than static strings.

**Details**

Drafts can be generated and edited, but the surrounding operator experience (tone presets, channel-specific tweaks, ready-to-send states) is still rudimentary. Integrating the site preview and brief context directly into the editing surface will satisfy the remaining items.

## Phase 15: Premium Preview Delivery and Refinement

Goal:

- make generated previews production-ready by turning extracted site data and visual redesign briefs into premium, bespoke page output.

Deliverables:

- component-driven preview rendering that uses `section.componentId`.
- premium Tailwind/ShadCN/Codedrop-inspired section layouts for hero, services, proof, gallery, process, and CTA panels.
- full-page screenshot capture of the generated preview.
- screenshot-based QA analysis and score for preview quality.
- public preview URL generation with admin visibility.
- backend preview metadata for screenshot and quality status.
- frontend preview workspace that displays generation progress, quality score, and shareable preview links.

Exit criteria:

- generated previews render premium layouts with the recommended component assignments.
- preview pages are visually distinct, non-repetitive, and aligned with extracted brand assets.
- a full-page screenshot is captured and analyzed for each preview.
- low-quality or incomplete previews are flagged before being published.
- the frontend and backend are stable enough for production staging.

## Phase 16: Operator-Driven Redesign and Regeneration

Goal:

- enable operators to refine previews from the admin by submitting natural-language redesign prompts and regenerating the design.

Deliverables:

- admin prompt panel for preview refinement.
- backend endpoint to regenerate a preview from operator instructions.
- prompt history and preview version metadata.
- safe regeneration workflow that preserves brand token integrity and source content.
- UI feedback for prompt status, regeneration progress, and preview quality.
- public preview replacement only after QA success.

Exit criteria:

- operators can submit a redesign prompt in the admin and receive a new preview.
- prompt inputs are persisted and linked to the generated preview version.
- the regeneration pipeline can rerun safely without invalid output.
- preview updates are visible in the admin and exposed to public share links.
- the system supports multiple prompt-led refinement iterations.

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

### Implementation status

**Checklist**

- [x] Analytics ingestion + aggregation repository stubs (`core/analytics.py`).
- [x] API routes + auth for `/api/analytics/*` (router imported but endpoints not implemented yet).
- [x] Frontend analytics dashboard (current page is a placeholder panel `apps/web/src/app/nsa/analytics/page.tsx`).
- [x] Client instrumentation in previews / admin actions.

**Details**

Data models for events, summaries, and metrics feed a live dashboard. The FastAPI analytics router enforces auth, admin actions emit structured analytics events, preview clients send visit/click instrumentation, and the repository prunes events older than 45 days to keep the dataset lean.

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

### Implementation status

**Checklist**

- [x] Job queue/worker health dashboards and retry tooling beyond basic `/jobs/health`.
- [x] QA review queues, screenshot storage, regeneration controls.
- [x] Theme/palette diversity instrumentation and automation handoff records.

**Details**

Operators now have a dedicated Scale surface (`/nsa/scale`) that consumes `/api/jobs/health`, surfaces stalled/failed jobs by type, and lets reviewers retry any job with audit-friendly notes. The QA review queue lives at `/nsa/review`, backed by `/api/sites/review-queue`, `/api/sites/:id/review`, and `/api/sites/:id/review/approve`: reviewers can load checklist-backed site records, add screenshot provenance, trigger regenerations, and push approved previews through the automation handoff flow. The review queue response now emits theme/palette diversity metrics plus automation readiness counts so palette drift and publish-ready previews stay visible; the UI highlights handoff-ready sites and the backend records explicit handoff metadata tied to each approval.

## Implementation Order Recommendation

1. Auth and shell
2. Lead intake
3. Discovery and extraction
4. Briefing and review
5. Generation, preview rendering, and design QA
6. Messaging drafts
7. Analytics
8. Scale hardening
