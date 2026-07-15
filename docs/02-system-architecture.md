# System Architecture

## Stack

- Backend: Python
- Frontend: Next.js
- UI system: Tailwind CSS + shadcn/ui
- Database: MongoDB
- Internal auth: email allowlist from environment configuration
- Analytics: internal event tracking with page-view and engagement events

## High-Level Components

### 1. Admin Web App

The admin UI is the operator surface for the whole system.

It should support:

- lead ingestion
- job monitoring
- site review
- generated preview browsing
- outreach copy review
- analytics review
- authentication and session management

### 2. Python Backend

The backend is responsible for:

- ingesting imports
- crawling websites and sitemaps
- extracting content and brand data
- generating normalized records
- orchestrating AI-assisted generation workflows
- persisting data to MongoDB
- serving data and analytics to the frontend
- enforcing internal authorization rules

### 3. MongoDB

MongoDB stores all durable application state:

- leads
- extracted website snapshots
- generation jobs
- generated site definitions
- messaging drafts
- analytics events
- auth allowlist metadata
- audit logs

### 4. Generated Site Runtime

Each lead/company gets a rendered preview site, typically under a route pattern like:

- `sites.lenquant.com/[company-slug]`

These pages are driven by generated content and design configuration stored in MongoDB.

This is a single renderer serving many generated sites, not a separate application per company.
The renderer should consume a site document, a theme variant, a runtime context, and any approved override records, then assemble the page dynamically.

### 5. Site Override and Export Layer

This layer is what makes the system practical for real operator edits.

It should support:

- storing manual changes as structured overrides instead of rewriting generated output in place
- merging overrides into the rendered site document at build or preview time
- regenerating a preview without losing approved edits
- exporting a site snapshot to a local folder, GitHub repo, or other handoff format
- recording which edits came from the operator versus the generation engine

The editable source of truth should be the site spec plus override records, not the rendered page HTML itself.

### 6. Analytics Pipeline

Analytics must answer:

- was the preview visited
- which pages were visited
- how long visitors stayed
- which CTA was clicked
- whether a Calendly link or booking event was reached
- which outreach source sent the visitor

## Request Flow

### Lead Creation

1. User uploads CSV or enters a URL.
2. Frontend submits data to backend.
3. Backend creates a lead record in MongoDB.
4. Backend queues discovery and extraction jobs.
5. Frontend shows status updates from the job record.

### Site Discovery

1. Backend resolves the lead website.
2. Backend reads sitemap URLs first when available.
3. Backend crawls homepage and relevant internal pages from public HTML only.
4. Backend stores normalized extraction output, source references, and crawl confidence.

### Generation

1. Backend converts extracted data into a structured site brief.
2. Backend chooses a layout strategy, theme family, and content strategy.
3. Backend generates section data, CTA copy, motion guidance, and design tokens.
4. Backend stores the generated site document and its rationale.
5. Operator reviews the preview and can add structured overrides.
6. Backend regenerates the preview from the site document plus overrides.
7. Frontend renders the preview using the merged result.

### Export and Handoff

1. Operator marks a preview ready for export or sharing.
2. Backend creates a site snapshot or export bundle.
3. Backend records the export target, commit, path, or URL.
4. Frontend shows export status and sync state.

### Outreach Preparation

1. Backend generates messaging variants.
2. Frontend displays recommended message templates.
3. Admin can copy, edit, or mark a draft as ready.

### Analytics

1. Preview page sends page-view and interaction events.
2. Backend stores them in MongoDB.
3. Frontend admin queries and aggregates them into useful charts and tables.

## Design Principle

Backend and frontend must stay aligned through shared data contracts.

That means:

- no frontend-only magic data assumptions
- no backend fields that the UI cannot render
- no UI sections without a backend source
- no analytics event without a defined consumer in the admin

## Multi-tenant Model

The platform should behave like a single internal system with many generated companies, not many separate apps.

One codebase should handle:

- the admin
- the generated previews
- lead-specific content
- site-specific branding
- site-specific outreach copy

## Routing Model

Recommended route structure:

- `/nsa` for internal admin
- `/nsa/leads`
- `/nsa/leads/[id]`
- `/nsa/sites/[id]`
- `/nsa/sites/[id]/brief`
- `/nsa/messages`
- `/nsa/analytics`
- `/nsa/sites/[id]/edit`
- `/sites/[slug]` for public preview rendering
- `/sites/[slug]/[page]` only if multi-page previews are enabled later

## Implementation status

**Checklist**

- [x] Monorepo layout with Next.js admin + FastAPI backend matches the documented component map (`apps/web`, `apps/backend`).
- [x] Shared API router wiring all feature modules (`apps/backend/app/api/router.py`) reflects the routing model above.
- [x] Mongo connection helpers exist and are used opportunistically (`app/core/mongo.py`), though optional for local development.
- [x] Generated preview runtime + override/export layer are live via the public preview API (`/api/public/sites/[slug]`), client-side analytics instrumentation, and the admin export workspace.
- [x] Background job/extraction orchestration now runs through the shared async queue (`app/core/job_queue.py`) so crawls are queued and reported via the jobs API.
- [x] Analytics ingestion/storage pipeline is wired end-to-end: the preview runtime emits events, `/api/analytics` stores them, and the NSA analytics surfaces visualize the rollups.

**Details**

The foundation (admin app, backend services, schemas) mirrors the target architecture, so developers can build features against the documented contracts. Background crawls are now queued and executed asynchronously, updating the jobs endpoint as they progress. Operators can review and export live previews through the public renderer, override workspace, and export controls, while preview visitors trigger analytics that flow into the `/api/analytics` dashboard. The remaining architectural pieces—namely resilient generation workers beyond extraction and deeper multi-tenant publishing infrastructure—are the next focus to fully harden the system.
