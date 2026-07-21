# LenQuant Website Fabric

LenQuant Website Fabric is an internal, AI-assisted growth operating system for turning leads into polished website previews, tailored outreach messaging, and measurable sales-ready assets. It sits at the intersection of sales enablement, content generation, and marketing operations: operators can ingest a lead, research the target company from public web signals, generate a conversion-focused preview site, review it in a controlled workspace, and use that output to support outreach conversations.

This project is not a generic landing page builder. It is a multi-step revenue workflow platform designed to help a small team create better first impressions for prospective clients at speed.

## What the product actually does

At a high level, LenQuant Website Fabric helps an operator move from a lead or URL to a compelling, tailored website experience in a matter of minutes.

### Core workflow

1. Lead intake
   - Accept a lead manually or through a structured import flow.
   - Capture the target company, contact, website URL, and supporting context.
   - Normalize the lead into a reusable internal record.

2. Website intelligence
   - Resolve the company website from the input.
   - Crawl public site content and sitemap structure where available.
   - Extract signals about positioning, messaging, audience, services, visual identity, and calls to action.
   - Build a structured brief that summarizes what the target business is saying and what could be improved.

3. Preview site generation
   - Turn the discovered insights into a generated website concept.
   - Produce conversion-aware page sections, styles, CTAs, messaging, and layout structure.
   - Render a preview experience that can be reviewed internally before the asset is shared.

4. Operator review and editing
   - Let operators inspect generated content and adjust it through a controlled edit layer.
   - Preserve manual overrides so regeneration does not overwrite approved changes.
   - Keep the generated experience aligned with the original source material while allowing human refinement.

5. Outreach and handoff
   - Generate tailored messaging drafts for outreach campaigns.
   - Provide a preview that can be used during sales conversations, discovery calls, or follow-up communication.
   - Support export or sharing workflows so the asset can move from internal review to external use.

6. Analytics and measurement
   - Track preview engagement and visitor behavior.
   - Record page views, interaction signals, and campaign attribution.
   - Give operators feedback on whether the generated experience is getting attention and where it is resonating.

## Product positioning

LenQuant Website Fabric is a revenue acceleration platform for agencies, operators, and growth teams that need to quickly turn a lead into a credible, polished digital presence.

Its value is not only the final preview website. The platform also compresses the workflow of:

- understanding the lead's business,
- translating that understanding into a marketable message,
- generating a relevant website experience,
- and preparing a more confident outreach motion.

In other words, it turns a fragmented sales and marketing process into a guided, repeatable engine.

## Key functionalities

### 1. Lead and company management

The system stores lead records and related company context so an operator can move through a full lifecycle without starting from scratch each time.

Typical capabilities include:

- creating and reviewing leads,
- storing company and contact context,
- tracking generated assets against each lead,
- monitoring the status of extraction and generation jobs.

### 2. Website discovery and content extraction

The backend is designed to work from public web data to understand the brand narrative before generation starts.

This includes:

- resolving a target website,
- reading homepage and internal page content,
- using sitemaps when available,
- detecting public brand signals such as language, structure, CTAs, and positioning,
- generating a normalized internal brief.

### 3. AI-assisted site generation

The platform uses structured generation logic to turn extracted insights into a site concept that feels more tailored than a generic template.

Generated outputs can include:

- hero section messaging,
- service or offer framing,
- conversion-oriented body sections,
- CTA language,
- brand-aware visual structure,
- page-level layouts and content blocks.

### 4. Preview rendering and override management

The preview layer is a first-class part of the product. Operators can review a generated experience without immediately shipping it to the public.

The platform supports:

- internal preview delivery,
- review of generated content,
- manual overrides for specific sections or components,
- regeneration without losing approved edits.

### 5. Messaging and outreach support

The platform is built not only for site generation, but for the broader outreach workflow that follows.

It can support:

- message variants for LinkedIn, WhatsApp, or email,
- copy that references the generated preview,
- more contextual and relevant sales outreach than default templates.

### 6. Analytics and performance insight

The product includes instrumentation for measuring what happens after a preview is shared.

It supports:

- visitor page views,
- interaction events,
- content engagement signals,
- campaign or source attribution,
- internal reporting for operators and stakeholders.

## Technology stack

### Frontend

- Next.js 15 for the operator experience and app shell
- React 18 for interactive UI components
- Tailwind CSS for utility-first styling
- shadcn/ui-style component patterns for polished internal interfaces
- Framer Motion and related UI libraries for richer animated experiences

### Backend

- Python 3.11+
- FastAPI for the API layer
- Pydantic for request and response validation
- MongoDB for durable storage of leads, jobs, generated content, and analytics
- Celery + Redis for async background jobs
- AI-backed generation flows using model providers such as Bedrock and Gemini depending on environment

### Infrastructure and deployment

- Docker Compose for local and production orchestration
- Nginx reverse proxy support
- Optional external services for email, payments, and storage depending on deployment needs

## Architecture at a glance

The repository is organized as a monorepo with three major components:

- apps/web: the operator-facing web experience
- apps/backend: the API, business logic, job orchestration, and data persistence
- apps/compiler: the service layer for compiled or generated preview assets

The system follows a single-codebase model in which the admin experience and the generated preview runtime share the same underlying product logic rather than being split into many disconnected apps.

## How the system is meant to be used

A typical operator flow looks like this:

1. Create or import a lead.
2. Review the target company context and website.
3. Trigger research and extraction jobs.
4. Review the generated brief and proposed site structure.
5. Preview the generated site inside the internal workspace.
6. Make manual improvements through the override layer.
7. Regenerate the preview if needed.
8. Share the output for outreach or handoff.
9. Monitor engagement and use the evidence to refine the next round.

## Local development

### Prerequisites

- Node.js and npm
- Python 3.11+
- Redis for background jobs
- MongoDB access (local or remote)

### Install dependencies

```bash
npm install
cd apps/web && npm install
cd ../backend && pip install -e .
```

### Run the web app

```bash
npm run dev:web
```

### Run the backend

```bash
npm run dev:backend
```

### Run background workers

The platform uses Celery for discovery, extraction, and generation tasks.

```bash
cd apps/backend
celery -A app.core.celery_app.celery_app worker -l info
```

If you want background tasks to execute inline during local tests, set:

```bash
CELERY_TASK_ALWAYS_EAGER=true
```

## Environment configuration

The app expects a set of environment variables for database access, auth, AI providers, and background services. Typical values include:

- MongoDB connection details
- JWT or session secret configuration
- allowlist-based auth settings
- Redis broker URL for Celery
- AI provider credentials and model settings

## Why this project matters

LenQuant Website Fabric exists to compress the time between:

- discovering a lead,
- understanding their positioning,
- producing a credible digital experience,
- and engaging them with a more relevant message.

It is designed for operators who need to move quickly, make thoughtful decisions, and create output that feels customized rather than templated.

## Project goals

The long-term direction of the project is to become a dependable internal operating system for:

- lead-to-preview conversion,
- AI-assisted content and site generation,
- internal review and approval workflows,
- outreach preparation,
- and measurable marketing performance.

## Repository structure

- apps/web: frontend application and operator UI
- apps/backend: API, business logic, job workers, and persistence
- apps/compiler: compilation and rendering service layer
- docs: product vision, architecture, workflow, and implementation notes

## Summary

LenQuant Website Fabric is a practical, AI-assisted platform for building high-quality preview experiences for leads and prospects. It combines web intelligence, generative content workflows, operator review tools, outreach support, and analytics into one system so a team can move from opportunity to polished presentation with far less friction.

