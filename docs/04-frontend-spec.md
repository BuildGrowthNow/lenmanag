# Frontend Specification

## Frontend Goals

The frontend is the internal control center plus the preview renderer.

It must:

- let users manage large lead batches
- show job progress clearly
- render generated websites beautifully
- expose analytics and outreach data
- keep the system fast and usable under heavy content density
- let operators inspect the source website, extracted brief, generated output, and messaging side by side

## Frontend Stack

- Next.js
- Tailwind CSS
- shadcn/ui
- server components where appropriate
- client components for interactive dashboards and analytics controls

## Visual Direction

The admin UI should feel:

- premium
- dense but readable
- operationally clear
- intentionally styled
- responsive for desktop-first use, with workable mobile support

The generated preview sites should feel:

- bespoke
- conversion-oriented
- brand-aware
- motion-rich without becoming decorative noise
- grounded in the source brand's logo, image style, color palette, and typography cues
- intentionally selected into a palette mode such as zinc, light, or colorful based on the extracted site
- production-ready, with no placeholder copy, demo assets, or fake claims

## Brand Input Contract

The frontend should treat these backend fields as first-class design inputs:

- extracted logo asset references
- source image and media references
- dominant and secondary color values
- typography cues and font recommendations
- visual tone notes
- inferred versus source-backed brand tokens
- palette mode recommendation
- contrast and saturation notes
- source visual style references

These inputs should be visible in the admin so operators can tell whether a preview is faithfully using extracted brand material or a fallback inference.

## Frontend Surfaces

### `/nsa` Dashboard

Main overview showing:

- total leads
- active crawl jobs
- generated sites ready
- messages ready for sending
- visits and CTA clicks
- recent errors

### `/nsa/leads`

Lead list and bulk management:

- CSV upload
- URL import
- filters by status
- search by company name or domain
- bulk actions

### `/nsa/leads/[id]`

Lead detail view:

- website detection result
- crawl health
- extracted content summary
- site brief preview
- brand signals
- generated preview link
- messaging drafts
- analytics snapshot
- job history
- source page inventory
- extraction confidence

### `/nsa/sites/[id]`

Generated site detail and preview management:

- hero variants
- section stack
- CTA strategy
- design tokens
- preview render
- version history
- generation rationale
- theme variant selection
- quality score
- before/after source comparison
- screenshot-backed QA status
- review notes and approval state
- selected palette mode
- source visual language summary
- override editor for operator changes
- regenerate preview action
- export or sync status to local/GitHub handoff
- diff view between source output and edited output

### `/nsa/sites/[id]/edit`

Site editing workspace:

- structured overrides for copy, layout, CTA, brand, motion, and styling
- before/after diff for each override
- revert and disable controls
- regeneration preview after edits
- export or snapshot action
- local handoff status if a repo or bundle has been created

### `/nsa/sites/[id]/brief`

Site intelligence review:

- extracted company summary
- inferred audience
- public source citations
- content gaps
- production blockers
- recommended conversion angle
- tone profile

### `/nsa/messages`

Outreach preparation center:

- channel-specific drafts
- tone and angle selection
- copy edit mode
- preview link mapping
- calendly link visibility
- draft rationale and personalization notes

### `/nsa/analytics`

Analytics dashboard:

- total page views
- unique visitors
- CTA clicks
- session trends
- source breakdown
- per-site conversion events
- lead-to-message-to-visit funnel

## Generated Site Rendering Requirements

The generated site renderer should be able to:

- render variable hero layouts
- inject brand colors and logo assets
- support content blocks from the generation engine
- handle motion treatment selected per site
- display CTAs and contact sections
- support analytics event instrumentation
- support distinct layout families so consecutive sites do not feel cloned
- support responsive hero behavior with strong mobile composition
- support screenshot-based design review from the deployed preview URL
- expose enough metadata for a review agent to compare the preview against the source website and brief
- render either zinc, light, or colorful modes depending on the source-derived design decision

## Admin UX Requirements

- Status should be visible at a glance.
- Every lead should show its current pipeline stage.
- Every generated site should be previewable from the row or detail page.
- Analysts or operators should be able to compare version history.
- Copy actions should be quick and obvious for outreach.
- Every major generated decision should be traceable back to source material.
- Bulk actions should remain safe even when thousands of leads are imported.
- Review states should make it obvious when a site is blocked, needs visual changes, or is ready to publish.
- Source-derived brand cues should be visible alongside generated design decisions.
- Palette mode selection should be visible so operators can see whether a site intentionally stayed minimal or moved into a more colorful treatment.

## Component Strategy

Use reusable shadcn/ui primitives for:

- tables
- dialogs
- drawers
- tabs
- badges
- progress indicators
- code-like previews
- collapsible panels
- toasts

Use custom components for:

- lead pipeline cards
- preview device frames
- brand token displays
- analytics charts
- section stack previews
- CTA message editors
- screenshot comparison cards
- review note panels
- source brand evidence tiles
- missing-field review tiles
- production-readiness status chips
- override diff panels
- export status cards

## Frontend-Backend Coupling Rules

Every screen must be backed by explicit API data.

Examples:

- The dashboard cards must map to aggregate API endpoints.
- The lead detail page must fetch lead, extraction, generation, messaging, and analytics resources.
- The preview page must receive the rendered site document, approved overrides, plus required runtime metadata.
- The analytics page must read event collections or aggregated summaries, not fictionalized counts.
- The QA surface must fetch the review payload, deployed preview URL, and comparison metadata from the backend.
- The edit surface must persist changes as override records and never rely on rendered HTML as the system of record.
- No generated visual should depend on frontend-only assumptions about brand colors, typography, or images.
- Missing information must render as explicit admin review states, not placeholder UI or fake preview content.

## Implementation status

**Checklist**

- [x] Next.js admin shell, navigation, and primary workspaces (`/nsa`, `/nsa/leads`, `/nsa/sites/[id]`, `/nsa/messages`) exist and match the documented surfaces.
- [x] Shared design system + gradients + shadcn primitives implemented in `apps/web/src/components/*` with premium styling.
- [x] Lead detail, analytics, and edit workspaces now surface deep inspection tools (extraction review + citations on lead detail, fully wired analytics dashboard, structured override editor on `/nsa/sites/[id]/edit`).
- [x] Generated preview renderer (public `/sites/[slug]`) ships with the live redesign experience, traceability sidebars, and analytics instrumentation.
- [x] Operator diff/export controls are wired: override panels list versioned records/previews and export cards allow recording + downloading bundles.

**Details**

The current frontend now covers the Phase 4 expectations: lead detail exposes extraction review + citation drilling, the analytics workspace renders real dashboard data, the edit workspace provides structured override/diff tooling, and the public preview renderer is shipping with traceability + instrumentation. Remaining gaps live in later phases (preview QA automation, deeper diff tooling), but the Phase 4 UI surfaces are production-ready.
