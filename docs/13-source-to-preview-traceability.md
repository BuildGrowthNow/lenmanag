# Source-to-Preview Traceability

## Purpose

Operators must be able to point at any UI affordance and show where the data originated, how it was interpreted, and which overrides were applied before outreach. This document enumerates the lineage across backend collections, API responses, and frontend surfaces so reviewers never have to guess how a preview was assembled.

## Lineage summary

1. **Lead intake → extraction**
   - Sources: `leads`, `site_extractions` (`apps/backend/app/core/leads.py`, `app/core/extraction.py`).
   - APIs: `POST /api/leads`, `POST /api/leads/{id}/extract` (`app/api/leads.py`).
   - UI: lead intake form, extraction status cards inside `apps/web/src/app/nsa/leads/[id]/page.tsx`.

2. **Extraction → brief**
   - Transformation: extraction snapshots are normalized into `SiteBrief` objects via the summarizers in `app/core/sites.py` (`_site_refs`, `_brand_tokens`, `_theme_for_signals`).
   - APIs: `GET /api/leads/{id}/brief`, `POST /api/leads/{id}/brief/approve`.
   - UI: `apps/web/src/components/lead-brief-review.tsx` exposes `brief.sourceCitations` and `brief.brandAssetProvenance`, keeping raw excerpts adjacent to the interpreted value.

3. **Brief → generated preview**
   - Transformation: `site_repository.generate_site` in `app/core/sites.py` merges the approved brief with override history and theme data to create `GeneratedSite` responses, attaching `site.sourceTraceability` (page + asset references) and `brandTokens`.
   - APIs: `POST /api/sites/{siteId}/generate`, `GET /api/sites/{siteId}` (`app/api/sites.py`).
   - UI: operator preview (`apps/web/src/app/nsa/sites/[id]/page.tsx`) shows traceability badges while the public preview (`apps/web/src/app/sites/[slug]/page.tsx`) exposes a trimmed read-only version.

4. **Overrides + exports**
   - Sources: `site_overrides`, `site_exports` repositories (`app/core/sites.py`).
   - APIs: `POST /api/sites/{siteId}/overrides`, `POST /api/sites/{siteId}/export`.
   - UI: `SiteWorkspaceControls` (`apps/web/src/components/site-workspace-controls.tsx`) lets operators push overrides + exports while `/nsa/sites/[id]` shows the resulting metadata next to the rendered preview.

5. **Outreach + analytics**
   - Sources: `messaging_drafts`, `analytics_events` (`app/core/messages.py`, `app/core/analytics.py`).
   - APIs: `/api/messages`, `/api/analytics/events` and `/api/analytics/dashboard`.
   - UI: outreach composer (`apps/web/src/app/nsa/messages/[id]/page.tsx`) references the same lead + site objects, while the analytics dashboard (see plan below) shows which previews have visits/CTAs, tying outcomes back to the generated surface.

## UI affordance mapping

| UI affordance | Dataset / field | Backend owner | Frontend consumer |
| --- | --- | --- | --- |
| Brief source citations & brand cues | `SiteBrief.sourceCitations`, `SiteBrief.brandAssetProvenance` | Built inside `_site_refs` and `_brand_tokens` (`app/core/sites.py`) using extraction snapshots | `apps/web/src/components/lead-brief-review.tsx`, `apps/web/src/app/nsa/sites/[id]/brief/page.tsx` render citations and provenance with confidence badges |
| Preview hero colors, typography, and CTA copy | `GeneratedSite.brandTokens` + `sections` produced by `site_repository.generate_site` | `_brand_tokens`, `_theme_for_signals`, `_palette_mode_from_signals` in `app/core/sites.py` | Operator preview (`apps/web/src/app/nsa/sites/[id]/page.tsx`) and public preview (`apps/web/src/app/sites/[slug]/page.tsx`) bind directly to the tokens |
| Traceability sidebar | `GeneratedSite.sourceTraceability` aggregated from brief + extraction references | `_site_refs` + `_dedupe_refs` in `app/core/sites.py` | Operator preview + lead brief pages render `sourceTraceability` arrays with the same shape |
| Override callouts | `SiteOverrideRecord` history | `create_override` + `retry_generation` in `app/core/sites.py` merge overrides during render | `SiteWorkspaceControls` + `apps/web/src/app/nsa/sites/[id]/page.tsx` highlight manual changes and link back to their sources |
| Outreach snippets | `messaging_drafts` referencing `leadId` + `siteId` | `app/core/messages.py` ensures message drafts denormalize the CTA + conversion angle | `apps/web/src/app/nsa/messages/[id]/page.tsx` mirrors the same data, showing which section or CTA motivated the draft |
| Analytics rollups | `analytics_events` rolled up through `AnalyticsRepository.get_dashboard` | `app/core/analytics.py`, `app/api/analytics.py` | `/nsa/analytics` surface (see instrumentation doc) consumes `AnalyticsDashboardResponse` |

## Operator traceability workflow

1. **Capture** – When an extraction finishes, the `sourceMap`, `brandAssetCues`, and `sourceCitations` fields are persisted with lead IDs, so every later step can link back to the raw page URL.
2. **Interpret** – The brief surfaces (NSA lead brief page) show each interpreted statement with badges describing whether the content is source-backed or inferred, and let reviewers drill into the snippet before approving the brief.
3. **Generate** – Preview generation produces `GeneratedSite` objects that carry forward the citation arrays. The operator preview renders those arrays inline next to the rendered section, so QA can see "where this came from" without leaving the page.
4. **Override** – Manual overrides reference the same `path` keys that the generator uses, so a preview always shows whether a given field is stock, inferred, or overridden.
5. **Outcomes** – Analytics events (see next checklist) pair visit data with `leadId`, `siteId`, `variantKey`, and message IDs, so success metrics can always be traced back to the exact preview and outreach asset that produced them.

## Gaps to monitor

- **Missing references**: the operator UI already displays empty states when no citation exists; continue flagging those so the brief cannot be approved blindly.
- **Override conflicts**: override records include `previousValue` and `reason`. The review queue should ensure conflicting overrides are highlighted before publish.
- **Export provenance**: every export records commit metadata so external files can be traced back to their generated version and override set.

This document is now the canonical reference for explaining how any preview element ties back to its raw source. Mention it inside the product vision so operators know where to look during compliance reviews.

## Implementation status

**Checklist**

- [x] Lead → extraction → brief lineage persisted with citations, evidence labels, and inference flags (`app/core/leads.py`, `app/core/sites.py`).
- [x] Site workspace + brief review surfaces display source references and missing requirements inline (`apps/web/src/app/nsa/sites/[id]/page.tsx`, `apps/web/src/components/lead-brief-review.tsx`).
- [x] Override and export records include provenance + diff metadata so operators can explain every manual change (`app/core/sites.py#create_override`, `site_exports`).
- [ ] Analytics + messaging dashboards link outcomes back to specific source citations (analytics exists, but source-level slice is not yet surfaced in UI).
  - **Backend changes needed:**
    - File: `apps/backend/app/core/analytics.py`
    - Extend `AnalyticsEventCreateRequest` schema to include optional fields:
      - `sourceCitationId: str | None` - ID of the source citation that motivated the event
      - `sourceUrl: str | None` - direct URL reference to the source page
      - `evidenceType: str | None` - type of evidence (title, meta, heading, cta, etc.)
    - Modify `ingest_event()` to store these new fields in the event document
    - Add a new method `get_source_attribution(site_id: str, lead_id: str) -> SourceAttributionReport` that:
      - Aggregates events by source citation ID
      - Returns which source pages drove the most engagement
      - Shows which evidence types (title, meta, heading) correlate with CTA clicks
      - Links analytics outcomes back to specific source citations
    - Extend `AnalyticsDashboardResponse` schema to include:
      - `sourceAttribution: list[SourceAttributionSummary]` - per-source engagement metrics
      - `evidenceTypePerformance: dict[str, EvidenceMetrics]` - performance by evidence type
    - File: `apps/backend/app/api/analytics.py`
    - Add endpoint `GET /api/analytics/sites/{site_id}/source-attribution` for per-site source attribution
    - Add endpoint `GET /api/analytics/leads/{lead_id}/source-attribution` for per-lead source attribution
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/analytics/page.tsx`
    - Add a new card section "Source Attribution" showing:
      - Top source pages by engagement (visits, CTA clicks)
      - Evidence type performance (which types of evidence drive conversions)
      - Source citation → outcome mapping (e.g., "Homepage title → 12 visits, 3 CTA clicks")
    - File: `apps/web/src/app/nsa/sites/[id]/page.tsx`
    - In the analytics section (if exists), show source attribution for that specific site
    - Link each source citation in the traceability sidebar to its analytics performance
    - Add badges to source citations showing engagement metrics (e.g., "8 visits", "2 CTA clicks")
    - File: `apps/web/src/app/nsa/messages/[id]/page.tsx`
    - When viewing a message draft, show which source citations motivated the draft
    - Display analytics for those citations (visits, conversions)
  - **What already exists:**
    - `AnalyticsEvent` schema has siteId, leadId, sessionId fields
    - `SourceCitation` schema exists with id, pageUrl, evidenceType, excerpt
    - `GeneratedSite.sourceTraceability` contains source references
    - Analytics dashboard exists with site/lead/variant metrics
  - **What needs to be done:**
    - Extend analytics events with source citation fields
    - Add source attribution aggregation logic
    - Create source attribution API endpoints
    - Build source attribution visualization in analytics dashboard
    - Link source citations to their performance metrics
    - Show source attribution in messaging workspace

- [ ] Compliance-ready traceability matrix tying every persisted field to source data (Phase 0 checklist still open; needs automation beyond narrative doc).
  - **Backend changes needed:**
    - File: `apps/backend/app/core/traceability_matrix.py` (new file)
    - Create a new class `TraceabilityMatrixGenerator` with methods:
      - `generate_field_traceability() -> FieldTraceabilityReport` that:
        - Iterates over all persisted schemas (Lead, ExtractionSnapshot, SiteBrief, GeneratedSite, SiteOverrideRecord, SiteExportRecord)
        - For each field, identifies its source (manual, inferred, source-backed, computed)
        - Maps each field to its source data (e.g., brief.companySummary.value → extraction.summary.positioningSummary → sourceCitations[0])
        - Generates a matrix showing field → source → citation chain
      - `export_traceability_matrix(format: str = "json") -> str` - exports the matrix in JSON or CSV format
      - `validate_traceability_coverage() -> TraceabilityCoverageReport` - checks that all fields have traceability documented
    - Add a new endpoint in `apps/backend/app/api/compliance.py` (new file):
      - `GET /api/compliance/traceability-matrix` - returns the full traceability matrix
      - `GET /api/compliance/traceability-coverage` - returns coverage report with gaps
      - `GET /api/compliance/traceability/{field_path}` - returns traceability for a specific field
    - File: `apps/backend/app/core/sites.py`
    - Add traceability metadata to each field in `GeneratedSite` schema:
      - Each field should have a `traceability: FieldTraceability` object with:
        - `sourceType: str` (manual, inferred, source_backed, computed)
        - `sourceField: str | None` - the field this was derived from
        - `sourceRecord: str | None` - the record type (extraction, brief, etc.)
        - `citationIds: list[str]` - IDs of source citations
    - Update all field assignment functions in `sites.py` to populate traceability metadata:
      - `_brand_tokens()` should add traceability to each token
      - `_hero_variant()` should add traceability to hero fields
      - `_section_stack()` should add traceability to section fields
      - `_cta_strategy()` should add traceability to CTA fields
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/compliance/page.tsx` (create if doesn't exist)
    - Create a compliance page with sections:
      - "Traceability Matrix" - table showing all fields and their sources
      - "Coverage Report" - showing which fields have traceability documented vs. gaps
      - "Field Lookup" - search for a specific field to see its traceability chain
    - File: `apps/web/src/app/nsa/sites/[id]/page.tsx`
    - Add a "Traceability" tab or modal that shows:
      - Full traceability matrix for the current site
      - Field → source → citation chain visualization
      - Coverage report for this specific site
    - Add traceability badges next to fields in the UI showing source type (manual, inferred, source_backed)
  - **What already exists:**
    - Traceability is documented narratively in this doc
    - `BriefEvidence` schema has sourceKind, inferenceLabel, references fields
    - `SiteToken` has evidence field with sourceKind and references
    - Source citations are stored in extraction and brief schemas
  - **What needs to be done:**
    - Create automated traceability matrix generator
    - Add compliance API endpoints
    - Extend schemas with per-field traceability metadata
    - Update field assignment functions to populate traceability
    - Build compliance UI page with matrix visualization
    - Add traceability lookup and coverage reporting
