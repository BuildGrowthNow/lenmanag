# Admin UX Specification

**Version:** 1.0  
**Date:** 2026-07-15  
**Scope:** Complete redesign of the `/nsa` admin panel across 4 implementation phases

---

## Overview

The admin is an internal operations tool used to process leads from discovery to published website. The core job is simple: take a company URL, extract intelligence, generate a personalized site, QA it, and publish it. Every UX decision should serve that pipeline.

### The Pipeline (mental model)

```
Add Lead → Extract → Brief → Generate Site → QA → Publish → Outreach
```

Every page in the admin maps to one or more steps in this pipeline. If a page doesn't map to a step, it's either an ops utility (belongs in a separate ops section) or it should be removed.

---

## Navigation

### Current problems
- "Route map" section in sidebar is useless (non-clickable URL pattern list)
- "Scale" is an ops utility sitting alongside user-facing pages
- No visual indication of where a lead is in the pipeline

### New sidebar structure

```
PIPELINE
  Dashboard
  Leads
  Websites
  Review
  Messages

OUTREACH
  Analytics

OPS  (collapsed by default)
  Scale
  Orders
```

**Remove entirely:** Route map section.

**Rules:**
- Active page is highlighted
- Pipeline section items show a small count badge (e.g. "Leads 12") for items needing attention
- Ops section is collapsed by default; expands on click

---

## Phase 1 — Lead Intake & Auto-Pipeline ✅ COMPLETE

**Goal:** When a lead is added, the system runs autonomously through extraction, brief generation, site generation, and QA without requiring manual steps. The operator only intervenes when something needs human judgement.

---

### Page: Leads List

**URL:** `/nsa/leads`

**Purpose:** Show all leads and their current pipeline stage at a glance. Let the operator add leads, spot blockers, and jump into any lead that needs attention.

#### Layout

**Top bar**
- Title: "Leads"
- Right: "Add Lead" button (primary), "Import CSV" button (secondary)

**Pipeline summary strip** (below title, above table)
- 6 small stat chips in a horizontal row:
  - `Processing` — leads currently running through any automated step
  - `Needs attention` — leads blocked or requiring human input
  - `Brief ready` — awaiting operator brief approval (if auto-mode is off)
  - `Site generated` — awaiting QA
  - `Ready to publish` — QA passed, not yet published
  - `Published` — done
- Clicking a chip filters the table to that stage

**Table**

| Column | Content |
|---|---|
| Company | Company name + domain (smaller, grey) |
| Stage | Pipeline stage badge (see stages below) |
| Status | What's happening right now (e.g. "Crawling page 3/6", "Brief approved", "QA failed") |
| Source | How the lead came in: Manual / CSV / API |
| Added | Relative timestamp (e.g. "2h ago") |
| Actions | Icon buttons: View, Archive |

Rows are sorted by most recent activity by default.

**Pipeline stage badges**

| Stage | Colour | Meaning |
|---|---|---|
| Extracting | Blue / animated | Crawl is running |
| Extracted | Blue | Crawl complete, brief not yet generated |
| Briefing | Blue / animated | Brief generation running |
| Brief ready | Yellow | Brief needs human review (manual mode only) |
| Generating | Purple / animated | Site generation running |
| QA | Purple | Site generated, QA scoring running |
| Ready | Green | QA passed, ready to publish |
| Published | Green / solid | Live |
| Needs attention | Red | Blocked — see lead detail for reason |
| Archived | Grey | Removed from active pipeline |

**Empty state:** "No leads yet. Add your first lead to get started."

---

#### Add Lead modal

Triggered by "Add Lead" button. A modal (not a new page).

**Fields**
- Website URL (required) — text input with URL validation
- Company name (optional) — pre-filled by extraction if left blank
- Mode toggle: **Auto** / **Manual**
  - Auto: system runs all steps without asking for approval
  - Manual: system pauses at Brief and QA steps for operator sign-off
- Notes (optional, collapsed by default — "Add notes ▾")

**Submit button:** "Add Lead"

On submit:
1. Lead is created with status `new`
2. Modal closes
3. Lead appears at top of table with stage `Extracting` and a progress indicator
4. Extraction starts automatically (no separate "Start crawl" step)

---

#### CSV Import modal

Triggered by "Import CSV" button.

**Fields**
- File upload (drag and drop or click)
- Mode toggle: Auto / Manual (applies to all imported leads)
- Preview table: shows first 5 rows parsed from the CSV with column mapping
- Column mapping dropdowns if headers don't match expected names

**Submit:** "Import N leads"

Progress shown inline as rows process. Results shown on completion: N created, N merged, N failed (with reason per failed row in an expandable section).

---

### Page: Lead Detail

**URL:** `/nsa/leads/[id]`

**Purpose:** Full view of a single lead. Shows the current pipeline stage prominently, lets the operator understand what the AI has found, approve or override decisions, and take actions.

#### Layout

**Header bar**
- Back link: "← Leads"
- Company name (large) + domain (smaller, grey)
- Pipeline stage badge (same badges as list)
- Top-right: action buttons relevant to current stage (see per-stage actions below)

**Main area: two columns**

Left column (narrower, ~35%): Lead info panels  
Right column (wider, ~65%): Current stage workspace

---

#### Left column panels

Each panel is a card. Cards are always visible regardless of pipeline stage.

**Identity card**
- Company name
- Website URL
- Industry (if available)
- Source: Manual / CSV / API
- Added: timestamp
- Version: N (if merged from multiple sources)

**Notes card**
- Editable text area
- Empty state: "Add a note..."

**Source refs** *(collapsed by default — "N source refs ▾")*
- List of source references (source type, ref string, import date)
- Only relevant if lead was merged from multiple imports

**Job history** *(collapsed by default — "View job history ▾")*
- List of all jobs linked to this lead
- Each job: type, status badge, start/finish time, error if failed
- Most operators will never need this — it's for debugging

---

#### Right column: stage workspace

This is the key innovation. The right column changes based on the current pipeline stage. It always shows exactly what matters now, with a clear action or a clear status.

---

**Stage: Extracting**

```
┌─────────────────────────────────────────┐
│ Extracting website                      │
│                                         │
│ ████████████░░░░░░░░  62%               │
│ Crawling page 4 of 6                    │
│                                         │
│ Pages found so far:                     │
│  ✓ Homepage                             │
│  ✓ /services                            │
│  ✓ /about                               │
│  → /contact  (crawling...)              │
│                                         │
│ [Cancel]                                │
└─────────────────────────────────────────┘
```

No action required. Auto-advances to next stage on completion.

---

**Stage: Brief ready** *(manual mode only)*

```
┌─────────────────────────────────────────┐
│ Brief — ready for review                │
│                                         │
│ Positioning                             │
│   [AI-generated summary text]           │
│                                         │
│ Audience                                │
│   [AI-generated text]                   │
│                                         │
│ Services                                │
│   [AI-generated text]                   │
│                                         │
│ Tone                                    │
│   [AI-generated text]                   │
│                                         │
│ CTA                                     │
│   [AI-generated text]                   │
│                                         │
│ ── Extraction evidence ▾ ──            │
│ (collapsed: pages crawled, confidence,  │
│  brand cues, gaps)                      │
│                                         │
│ [Reject — edit brief]  [Approve →]     │
└─────────────────────────────────────────┘
```

In **auto mode** this stage is skipped — brief is auto-approved by the AI.

"Reject — edit brief" opens an inline editor on the brief fields.  
"Approve →" sets brief to approved and triggers site generation.

**Extraction evidence** (collapsed section)
- Pages crawled: list with URL, status, confidence %
- Brand cues: colours, typography, logo candidates
- Gaps: any missing signals flagged
- Confidence badge: High / Medium / Low

---

**Stage: Generating**

```
┌─────────────────────────────────────────┐
│ Generating site                         │
│                                         │
│ ████████████████████  100%              │
│ Applying theme and sections...          │
│                                         │
└─────────────────────────────────────────┘
```

Auto-advances to QA stage on completion.

---

**Stage: QA**

```
┌─────────────────────────────────────────┐
│ Quality review                          │
│                                         │
│  Quality score   78 / 100               │
│  Theme           Nova                   │
│  Palette         Light                  │
│                                         │
│ ✓ Brief approved                        │
│ ✓ Source citations present              │
│ ⚠ Screenshot QA not yet run             │
│ ✗ Missing requirement: [detail]         │
│                                         │
│ [Preview site ↗]                        │
│                                         │
│ ── Site sections ▾ ──                  │
│ (collapsed: section list, component     │
│  assignments, section titles)           │
│                                         │
│ [Reject — regenerate]  [Approve →]     │
└─────────────────────────────────────────┘
```

In **auto mode**, if score ≥ threshold the site is auto-approved. Below threshold the AI can trigger one regeneration attempt before escalating to the operator.

Quality score shows contextual state:
- If no screenshot QA has run: "78 / 100 (no visual QA)" — not just "0"
- If blocked: score shows in red with list of blocking reasons

---

**Stage: Ready to publish**

```
┌─────────────────────────────────────────┐
│ Ready to publish                        │
│                                         │
│ Site passed QA with a score of 91/100   │
│                                         │
│ [Preview site ↗]  [Publish →]          │
└─────────────────────────────────────────┘
```

---

**Stage: Published**

```
┌─────────────────────────────────────────┐
│ Published                               │
│                                         │
│ [preview-slug.yourdomain.com ↗]         │
│ Published 3 hours ago                   │
│                                         │
│ [View messages →]  [View analytics →]  │
└─────────────────────────────────────────┘
```

---

**Stage: Needs attention**

```
┌─────────────────────────────────────────┐
│ ⚠ Blocked                               │
│                                         │
│ Reason: Homepage unreachable            │
│                                         │
│ The crawler could not reach the         │
│ website. Check that the URL is correct  │
│ and the site is publicly accessible.    │
│                                         │
│ [Edit URL]  [Retry extraction →]        │
└─────────────────────────────────────────┘
```

Each blocking reason has a tailored message and action.

---

### Auto-mode pipeline logic (backend)

When a lead is created in auto mode:

1. **Extraction** runs automatically
2. On extraction complete:
   - If confidence is High or Medium → auto-approve, proceed to brief generation
   - If confidence is Low → flag as "Needs attention" with reason, stop
3. **Brief generation** runs automatically
4. On brief complete:
   - Auto-approve brief (AI judges quality internally)
   - Proceed to site generation
5. **Site generation** runs automatically
6. On site generated:
   - If quality score ≥ threshold → auto-approve, mark "Ready to publish"
   - If quality score < threshold and no regeneration attempted → auto-regenerate once
   - If quality score < threshold after regeneration → flag as "Needs attention", stop
7. **Publish** is always a manual step (operator clicks Publish)

This means in auto mode, most leads arrive at "Ready to publish" with zero operator interaction.

---

## Phase 2 — Websites & Review ✅ COMPLETE

**Goal:** Give the operator a clear view of all generated sites and a structured QA workflow.

---

### Page: Websites

**URL:** `/nsa/sites`

**Purpose:** Library of all generated sites. Browse, filter, preview, and manage site readiness.

#### Layout

**Top bar**
- Title: "Websites"
- Filter chips: All / Blocked / Needs review / Ready / Published
- Right: search input (by company name or domain)

**Summary strip**
- `Ready to publish` count (green)
- `Needs QA` count (yellow)
- `Blocked` count (red)
- `Published` count (grey)

**Site cards grid** (or table — operator preference)

Each card:
```
┌────────────────────────────────┐
│ [Thumbnail / placeholder]      │
│                                │
│ Acme Corp                      │
│ acmecorp.com                   │
│                                │
│ Theme: Nova · Light            │
│ Score: 91/100  ✓               │
│ Status: Ready to publish       │
│                                │
│ [Open spec]  [Preview ↗]      │
└────────────────────────────────┘
```

Quality score display rules:
- Has screenshot QA: show `91/100` with pass/fail colour
- No screenshot QA: show `— / 100 (QA pending)` — never show "0"
- Blocked: show `Blocked` badge with reason on hover

---

### Page: Site Workspace

**URL:** `/nsa/sites/[id]`

**Purpose:** Full detail view for a single generated site. Review the spec, sections, sources, and brief. Take QA actions.

#### Layout

**Header**
- Company name + domain
- Status badge
- Quality score badge
- [Preview site ↗] button (always visible)
- [Approve] / [Reject] action buttons (when in QA state)

**Tabs**

| Tab | Content |
|---|---|
| Overview | Score breakdown, theme, palette, key metrics |
| Sections | List of sections with component, title, and source traceability |
| Brief | The approved brief that drove generation |
| Sources | Extraction evidence — pages crawled, citations, brand cues |
| History | Generation jobs and regeneration attempts |

**Overview tab**

```
Quality score: 91 / 100

✓ Brief approved (+2)
✓ Source citations (+1)
✓ Brand asset cues (+1)
✓ Screenshot QA: 88/100
⚠ 1 missing requirement (-3)

Theme: Nova
Palette: Light
Hero variant: headline-left

[Missing requirements ▾]
  • Low section title diversity
```

**Sections tab**

Table: Section name | Component | Title | Source citation | Status (check/warn/block)

**Brief tab**

Read-only view of the brief (positioning, audience, services, tone, CTA).  
Link: "← Back to lead" to see the extraction that produced it.

**Sources tab** *(collapsed subsections)*
- Pages crawled (URL, status, confidence, summary)
- Brand cues (colours, fonts, logo candidates)
- Extraction gaps
- Raw citations (per section)

---

### Page: Review Queue

**URL:** `/nsa/review`

**Purpose:** Screenshot-based visual QA for sites that need human review. Operators work through a queue of sites, approve or reject each.

#### Layout

**Header**
- Title: "Review queue"
- `N sites pending review`

**Queue item** (one at a time, full-width)

```
┌──────────────────────────────────────────────────────┐
│  Acme Corp · acmecorp.com                            │
│  Generated 2h ago · Theme: Nova · Score: 64/100      │
│                                                      │
│  ┌──────────────────────┐  Issues flagged:           │
│  │                      │  ⚠ Low section diversity   │
│  │   [Screenshot]       │  ⚠ Missing CTA component   │
│  │                      │                            │
│  └──────────────────────┘  [Preview site ↗]         │
│                                                      │
│  [← Skip]   [Reject — regenerate]   [Approve →]    │
└──────────────────────────────────────────────────────┘
```

**Approve:** marks site as `ready_for_review` → `ready_to_publish` (if score threshold met)  
**Reject — regenerate:** opens a short rejection form with reason, triggers regeneration  
**Skip:** moves item to end of queue

**Bottom panel** *(collapsed — "Batch diversity ▾")*
- Theme distribution chart
- Palette distribution chart
- Flag if any theme/palette is overrepresented

---

## Phase 3 — Outreach ✅ COMPLETE

**Goal:** Once a site is published, enable the operator to review and send outreach messages for each lead.

---

### Page: Messages

**URL:** `/nsa/messages`

**Purpose:** Draft, review, and manage outreach messages for published leads.

#### Layout

**Top bar**
- Title: "Messages"
- Filter: All / Draft / Edited / Ready
- Right: search by company

**Summary strip**
- `Total drafts` / `Edited` / `Ready to send`

**Lead list** (left column, ~30%)
- Each item: company name, domain, draft status badge
- Click to open message workspace on the right

**Message workspace** (right column, ~70%)

```
Acme Corp · acmecorp.com

Channel tabs: [Email] [LinkedIn] [Twitter]

──────────────────────────────────────────

Subject: [editable]

[Editable draft body]

──────────────────────────────────────────

Generated from: [brief title ↗]  [site preview ↗]

[Regenerate draft]  [Mark ready]
```

Draft statuses:
- `Draft` — AI-generated, not reviewed
- `Edited` — operator has modified it
- `Ready` — approved for sending

---

## Phase 4 — Analytics & Ops ✅ COMPLETE

**Goal:** Provide visibility into how published sites are performing and give the ops team tools to manage job health.

---

### Page: Analytics

**URL:** `/nsa/analytics`

**Purpose:** Show engagement data across all published sites.

#### Layout

**Top bar**
- Title: "Analytics"
- Date range picker: Last 7 days / 30 days / 90 days / Custom

**Summary strip**
- Total visits
- CTA clicks
- Unique sessions
- Booked calls

**Two-panel layout**

Left panel (top sites):
- Table: Site name, visits, CTA clicks, click rate
- Clicking a row filters the right panel

Right panel (selected site detail):
- Visit trend chart (sparkline)
- Traffic sources breakdown
- Section exposure list (which sections users saw)
- Outreach channel attribution (which message channel drove the visit)

**Lead attribution table** *(collapsed — "Per-lead attribution ▾")*
- Lead name, visits, CTA clicks, forms, booked calls, referrer

---

### Page: Scale (Ops)

**URL:** `/nsa/scale`

**Purpose:** Internal ops tool for monitoring Celery job queue health. Not part of the main pipeline flow.

**Navigation:** Lives under the "Ops" section of the sidebar, collapsed by default.

#### Layout

**Header**
- Title: "Queue health"
- Auto-refresh toggle (every 30s)

**Health strip**
- Queued / Running / Completed / Failed / Stalled

**Failed jobs list**
- Job ID, type, lead/site name, error summary, started, failed
- Per-row: [Retry] button

**Stalled jobs list** (running > 30 min)
- Same columns
- Per-row: [Kill & retry] button

**Job type breakdown** *(collapsed — "By job type ▾")*
- Table of job types with counts per status

---

### Page: Orders

**URL:** `/nsa/orders`

**Purpose:** Manage landing page orders (payments, delivery status). Ops utility.

**Navigation:** Lives under the "Ops" section alongside Scale.

No UX changes proposed in this spec — keep existing layout.

---

## Dashboard

**URL:** `/nsa`

**Purpose:** Daily overview. What needs attention right now.

#### Layout

**Header**
- Title: "Dashboard"
- Date: today

**Attention required** (top section, shown only if items exist)
- Cards for leads blocked, sites stuck in QA, failed jobs
- Each card has a direct action link

**Pipeline summary**
- Horizontal pipeline diagram: Extracting → Brief → Generating → QA → Ready → Published
- Count at each stage

**Recent activity feed** (last 24 hours)
- Timestamped list: "Acme Corp — site published", "TechCo — QA failed", etc.

**Queue health mini-panel** (compact version of Scale)
- Failed: N · Stalled: N · [View all →]

---

## Information hierarchy principles

These rules apply globally across all pages.

### Show by default
- Current state (what is happening now)
- The action the operator needs to take
- Counts and status badges
- Error messages and blocking reasons

### Collapse by default
- Historical data (job history, previous versions)
- Raw data and evidence (extraction pages, citations, source refs)
- Diversity and batch stats
- Technical details (job IDs, confidence raw values, component IDs)
- Notes and secondary metadata

### Never show
- Non-clickable route patterns (remove Route map entirely)
- Scores without context (never show "0/100" — explain why)
- Empty sections (hide cards/panels that have no data)
- Duplicate information (brief should appear once, not in both lead detail and site workspace simultaneously)

---

## Quality score display rules

The quality score is a composite metric that means different things at different stages. Display it consistently:

| State | Display |
|---|---|
| No site generated yet | — (no score shown) |
| Site generated, no screenshot QA | `~64 / 100` with tooltip "Estimated — screenshot QA pending" |
| Screenshot QA complete | `91 / 100` in green/yellow/red based on threshold |
| Site blocked | `Blocked` badge — score not shown (it's irrelevant) |

Thresholds:
- ≥ 90: green "Pass"
- 75–89: yellow "Review"
- 55–74: orange "Needs work"
- < 55: red "Blocked"

---

## Auto mode vs manual mode

This toggle is set per-lead at creation time and can be changed before the site is published.

| Step | Auto mode | Manual mode |
|---|---|---|
| Start extraction | Automatic (on lead creation) | Automatic (on lead creation) |
| Approve extraction | AI decides | Operator reviews and approves |
| Generate brief | Automatic | Automatic |
| Approve brief | AI decides | Operator reviews and approves |
| Generate site | Automatic | Automatic |
| QA site | AI decides (one retry if below threshold) | Operator reviews in Review queue |
| Publish | **Always manual** | **Always manual** |

In auto mode, the lead detail page shows what the AI decided and why, but doesn't ask the operator to do anything until "Publish."

---

## Implementation phases summary

### Phase 1 — Lead Intake & Auto-Pipeline ✅ COMPLETE
- ✅ Auto-trigger extraction on lead creation (`asyncio.create_task` in `create_lead`)
- ✅ Add mode toggle (Auto / Manual) to Add Lead modal and Import CSV modal
- ✅ Redesign lead detail page: stage-based right column with per-stage workspace
- ✅ Remove Route map from sidebar; restructure to Pipeline / Outreach / Ops sections with active-link highlighting
- ✅ Implement auto-pipeline logic (extraction → brief → site → QA with auto-approve thresholds)
- ✅ Fix quality score display (`~N/100` when no visual QA, never bare "0")

### Phase 2 — Websites & Review ✅ COMPLETE
- ✅ Redesign Websites page: filter chips, summary strip, fix quality score display (`~N/100` estimated, never bare "0", `Blocked` badge when blocked)
- ✅ Redesign Site workspace: tabs (Overview / Sections / Brief / Sources / History) with left column for generation controls
- ✅ Redesign Review queue: one-at-a-time QA flow with prev/next navigation, inline reject form, approve/skip actions
- ✅ Scale and Orders already in Ops section in sidebar (was done in Phase 1)

### Phase 3 — Outreach ✅ COMPLETE
- ✅ Redesign Messages page: lead list (30%) + channel workspace (70%) layout
- ✅ Channel tabs (Email / LinkedIn / WhatsApp) with per-channel dot indicator
- ✅ Draft status flow (Draft → Edited → Ready → Sent) with Mark ready / Mark sent / Reset actions
- ✅ Summary strip in list column (Total / Edited / Ready counts)
- ✅ Search by company + filter by status (All / Draft / Edited / Ready)
- ✅ Fix `calendlyUrl` save gap: added to `MessageDraftPatchRequest` schema (backend) and patch payload (frontend)
- ✅ Fix duplicate stat cards: removed from page, moved into workspace summary strip
- ✅ Fix analytics event type errors: added `message_marked_sent` and `message_reset_to_draft` to `AnalyticsEventType`
- ✅ Fix Pyright type error on `deliveryChannel` in `create_draft`

### Phase 4 — Analytics & Ops ✅ COMPLETE
- ✅ Redesign Analytics: two-panel layout (top sites table + site detail panel with drill-down), per-lead attribution collapsed by default, outreach channel attribution table, 4-stat summary strip (visits, CTA clicks, sessions, booked calls)
- ✅ Redesign Dashboard: attention-required section (blocked leads + failed/stalled job cards), pipeline summary diagram with live stage counts, recent activity feed (leads sorted by last update), engagement snapshot + queue mini-panel in right column, recent job failures surfaced inline
- ✅ Redesign Scale: auto-refresh toggle (30s interval, client-side polling via `getQueueHealth`), "Refresh now" manual button, failed jobs list with retry, stalled jobs list with "Kill & retry", job type breakdown collapsed by default, backlog snapshot card
- ✅ `analytics-dashboard.tsx` extracted as client component (interactive site selection) — analytics page stays a server component fetching once

---

*This document is the UX source of truth. Implementation prompts for each phase will reference this spec.*
