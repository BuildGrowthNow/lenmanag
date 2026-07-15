# Success Metrics & Analytics Instrumentation

## Purpose

This document converts the product-level success criteria (bulk throughput, preview engagement, differentiated output, outreach readiness) into instrumentation that already aligns with the existing FastAPI analytics endpoints and Next.js admin surfaces. It covers:

- the metrics we must report and how to compute them from existing schemas
- the client-side emitters needed on preview + admin routes
- the backend ingestion, storage, and aggregation stack (already present in `app/core/analytics.py`)
- dashboard wiring so operators can prove outcomes without duplicating logic across services

## Canonical KPIs

| KPI | Definition | Source |
| --- | --- | --- |
| **Lead throughput** | Leads processed per day/week from import → preview. `lead_imported`, `lead_created`, `site_generated` events grouped by day. | Analytics events + `jobs` for background progress. |
| **Preview engagement** | Unique sessions, CTA clicks, Calendly clicks per preview slug. Derived from `page_view`, `hero_cta_click`, `secondary_cta_click`, `contact_click`, `calendly_click` events keyed by `siteId`. | Analytics events. |
| **Differentiation coverage** | Number of previews with ≥3 unique `sourceTraceability` references + non-inferred palette tokens. Pulled from `GeneratedSite` records; surfaced via analytics dashboard using `/api/sites/{id}` prior to publish. | Sites API. |
| **Outreach readiness** | Messaging drafts that were marked ready after at least one preview visit within 48h. Join `message_marked_ready` events with visit events sharing `leadId`. | Analytics events. |
| **Override impact** | Count of `site_override_applied` events vs. regenerated previews to ensure overrides persist. | Analytics events. |

## Event taxonomy (no duplicates)

Use the existing `AnalyticsEventType` literal (`app/schemas/analytics.py`) so both preview and admin emitters share a single union. Each event must include `siteId`, `leadId`, `sessionId`, optionally `variantKey`, and structured `metadata` when extra context matters.

| Event type | Trigger | Required metadata |
| --- | --- | --- |
| `page_view` | Preview load (`apps/web/src/app/sites/[slug]/page.tsx`). Fire once per session per page. | `pagePath`, `referrer`, `utm`, `themeKey`, `variantKey`. |
| `hero_cta_click`, `secondary_cta_click`, `contact_click`, `calendly_click` | CTA interactions inside the generated preview surface (`apps/web/src/app/sites/[slug]/page.tsx` sections). | `sectionId`, `ctaLabel`, `ctaUrl`. |
| `section_exposure` | Intersection observer for hero/proof/services sections; throttle to once per section per session. | `sectionId`, `percentVisible`. |
| `form_interaction`, `outbound_link_click` | Optional forms/outbound links in preview. | `elementId`, `targetUrl`. |
| `lead_created`, `lead_imported` | Admin lead intake flows (`apps/web/src/app/nsa/leads/page.tsx`). | `sourceType`. |
| `site_generated`, `site_republished`, `generation_regenerated` | When operators run generation actions (`apps/web/src/app/nsa/sites/[id]/page.tsx`). | `themeKey`, `variantKey`. |
| `site_override_applied` | After overriding copy/layout (`SiteWorkspaceControls` in `apps/web/src/components/site-workspace-controls.tsx`). | `path`, `scope`. |
| `site_export_created` | Export modal confirm. | `exportType`. |
| `message_draft_edited`, `message_marked_ready` | Messaging workspace interactions. | `channel`, `messageId`. |
| `site_opened`, `brief_approved`, `brief_edited`, `theme_variant_changed` | Admin review interactions. | `view`, `variant`. |

## Frontend instrumentation plan

1. **Shared emitter**
   - Create `apps/web/src/lib/analytics/emitter.ts` exporting `track(event: AnalyticsEventCreateRequest)`.
   - Implementation: batch events in memory, POST to `/api/analytics/events` (via `safeRequest`) with retry + `navigator.sendBeacon` fallback for preview routes.
   - Avoid duplicating logic by sharing the same emitter between the public preview (edge runtime) and NSA routes; inject defaults (site/lead IDs) at call sites rather than building multiple emitters.

2. **Preview runtime hooks** (Next.js App Router)
   - Wrap preview layout (`apps/web/src/app/sites/[slug]/layout.tsx`) in a client component that initializes session + visitor fingerprint (UUID + localStorage) and fires `page_view`.
   - Section render helpers inside `apps/web/src/app/sites/[slug]/page.tsx` receive a `registerAnalytics` prop so CTA buttons can call `track("hero_cta_click", { sectionId, ctaLabel })` without duplicating code.
   - Use a single IntersectionObserver utility to emit `section_exposure` once per section per session.

3. **Admin runtime hooks**
   - NSA layout (`apps/web/src/app/nsa/layout.tsx`) attaches `site_opened` when a site detail page mounts; leads and brief actions dispatch their respective events right after the API mutation resolves.
   - Mutation hooks live alongside existing API clients (e.g., `apps/web/src/lib/api/sites.ts`). After any successful mutation (generate, override, export) call `track()` with the same payload instead of re-implementing audit logic.

4. **Type safety**
   - Export the generated `AnalyticsEventType` union from `@/lib/types` so TypeScript enforces correct event names across preview and admin components.

## Backend ingestion + aggregation

- **Ingestion**: `apps/backend/app/api/analytics.py` already exposes `/analytics/events`, `/analytics/dashboard`, `/analytics/sites/{id}`, `/analytics/leads/{id}`. No new endpoints are needed; the client simply posts `AnalyticsEventCreateRequest` objects.
- **Storage**: `AnalyticsRepository` writes to MongoDB (or an in-memory fallback). Ensure `MONGODB_URI` is set in production so the `_maybe_ensure_indexes` step creates indexes on `siteId`, `leadId`, and `sessionId`.
- **Aggregation**: `AnalyticsRepository.get_dashboard()` returns `AnalyticsDashboardResponse`, summarizing totals plus site/lead/variant/message metrics. This is the payload consumed by the NSA analytics page.
- **Retention**: Keep raw events indefinitely for now; add TTL indexes later once dashboards confirm we capture enough data (>90 days).

## Dashboard wiring

1. Replace `/nsa/analytics` placeholder (`apps/web/src/app/nsa/analytics/page.tsx`) with a real client component that calls `getDashboardSummary()` and renders:
   - KPI tiles (lead throughput, preview engagement, CTA conversions, outreach readiness)
   - Tables for "Leads with visits but no CTA", "CTA but no booked calls" (derived from `AnalyticsLeadMetrics`), "Top variants" (from `AnalyticsVariantMetrics`).

2. Provide deep links into `/nsa/sites/[id]` and `/nsa/leads/[id]` so operators can jump from a metric anomaly to the associated preview.

3. Gate the dashboard API behind `_require_session` (already in place) so only authenticated operators can view metrics.

## Operational safeguards

- **Sampling**: emitters default to 100% sampling. Add an environment toggle to disable instrumentation if APIs fail.
- **Error handling**: emitter retries up to 3 times and logs to `console.error` in development only.
- **PII**: events only reference company data (lead IDs, site IDs) and never include scraped customer emails.
- **Testing**: add integration tests for `/api/analytics/events` to ensure events are persisted and aggregated correctly (see `apps/backend/tests/test_analytics.py` when available).

With this plan, the analytics checklist in the Product Vision can be marked complete: the backend already owns ingestion/aggregation, while these steps define the production-ready frontend emitters and dashboards needed to prove success metrics end-to-end.

## Implementation status

**Checklist**

- [x] Analytics ingestion + aggregation stack implemented (FastAPI routes + `AnalyticsRepository.get_dashboard`).
- [x] NSA analytics dashboard consumes real metrics and surfaces KPIs + error feeds (`apps/web/src/app/nsa/analytics/page.tsx`).
- [ ] Preview + admin runtime emitters sharing a single client helper (preview still uses ad-hoc handlers; shared emitter pending).
  - **Frontend changes needed:**
    - File: `apps/web/src/lib/analytics/emitter.ts` (new file, replace existing analytics.ts)
    - Create a shared emitter class/function:
      ```typescript
      interface AnalyticsEvent {
        eventType: AnalyticsEventType;
        eventName: string;
        siteId?: string;
        leadId?: string;
        sessionId: string;
        visitorFingerprint?: string;
        themeKey?: string;
        variantKey?: string;
        messageId?: string;
        messageChannel?: string;
        pagePath?: string;
        referrer?: string;
        utm?: Record<string, string>;
        metadata?: Record<string, any>;
      }

      class AnalyticsEmitter {
        private queue: AnalyticsEvent[] = [];
        private flushInterval: number = 5000; // 5 seconds
        private maxQueueSize: number = 10;
        private sessionId: string;
        private visitorFingerprint: string;

        constructor() {
          this.sessionId = this.getOrCreateSessionId();
          this.visitorFingerprint = this.getOrCreateFingerprint();
          this.startFlushTimer();
        }

        track(event: AnalyticsEvent): void {
          // Add siteId, leadId, sessionId, visitorFingerprint if not provided
          const enrichedEvent = {
            ...event,
            sessionId: event.sessionId || this.sessionId,
            visitorFingerprint: event.visitorFingerprint || this.visitorFingerprint,
          };
          this.queue.push(enrichedEvent);
          if (this.queue.length >= this.maxQueueSize) {
            this.flush();
          }
        }

        private async flush(): Promise<void> {
          if (this.queue.length === 0) return;
          const events = [...this.queue];
          this.queue = [];
          try {
            await request("/api/analytics/events", { method: "POST", body: events });
          } catch (error) {
            // Re-queue failed events
            this.queue.unshift(...events);
            if (process.env.NODE_ENV !== "production") {
              console.warn("Analytics flush failed", error);
            }
          }
        }

        private startFlushTimer(): void {
          setInterval(() => this.flush(), this.flushInterval);
        }

        // Flush on page unload using sendBeacon
        flushOnUnload(): void {
          if (this.queue.length === 0) return;
          const blob = new Blob([JSON.stringify(this.queue)], { type: "application/json" });
          navigator.sendBeacon("/api/analytics/events", blob);
        }
      }

      export const analyticsEmitter = new AnalyticsEmitter();
      ```
    - File: `apps/web/src/lib/analytics/index.ts` (new file)
    - Export the shared emitter and convenience functions:
      ```typescript
      export { analyticsEmitter } from "./emitter";
      export function trackPageView(params: { siteId?: string; leadId?: string; pagePath: string; referrer?: string; utm?: Record<string, string> }) {
        analyticsEmitter.track({ eventType: "page_view", eventName: "Page view", ...params });
      }
      export function trackCtaClick(params: { siteId: string; leadId: string; ctaLabel: string; ctaUrl: string; sectionId?: string }) {
        analyticsEmitter.track({ eventType: "hero_cta_click", eventName: params.ctaLabel, ...params });
      }
      // Add other convenience functions for all event types
      ```
    - File: `apps/web/src/app/sites/[slug]/page.tsx`
    - Replace existing ad-hoc analytics calls with shared emitter:
      - Import `analyticsEmitter` from `@/lib/analytics`
      - Replace `sendAnalyticsEvent()` calls with `analyticsEmitter.track()`
      - Add `useEffect` to flush on unmount: `useEffect(() => () => analyticsEmitter.flushOnUnload(), [])`
    - File: `apps/web/src/app/nsa/layout.tsx`
    - Initialize shared emitter in NSA layout for admin events
    - Add flush on unmount for admin pages
    - File: `apps/web/src/components/site-workspace-controls.tsx`
    - Replace ad-hoc tracking with shared emitter convenience functions
    - File: `apps/web/src/app/nsa/sites/[id]/page.tsx`
    - Replace ad-hoc tracking with shared emitter
  - **What already exists:**
    - `apps/web/src/lib/analytics.ts` has basic `sendAnalyticsEvent()` function
    - Preview page has some analytics tracking (lines 108-111 in sites/[slug]/page.tsx)
    - Analytics API endpoint exists at `/api/analytics/events`
  - **What needs to be done:**
    - Create shared emitter class with batching and flush logic
    - Add convenience functions for common event types
    - Replace ad-hoc tracking in preview page with shared emitter
    - Replace ad-hoc tracking in admin pages with shared emitter
    - Add flush on page unload using sendBeacon
    - Ensure session and visitor fingerprint are consistent across pages

- [ ] Event coverage for CTA clicks, section exposures, and messaging states on every surface (some events exist, but taxonomy not fully wired client-side).
  - **Frontend changes needed:**
    - File: `apps/web/src/app/sites/[slug]/page.tsx`
    - Add CTA click tracking for all CTAs:
      - Hero primary CTA: `trackCtaClick({ siteId, leadId, ctaLabel: site.ctaStrategy.primary.label, ctaUrl: site.ctaStrategy.primary.href })`
      - Hero secondary CTA: `trackCtaClick({ siteId, leadId, ctaLabel: site.ctaStrategy.secondary.label, ctaUrl: site.ctaStrategy.secondary.href, eventType: "secondary_cta_click" })`
      - Footer CTA: `trackCtaClick({ siteId, leadId, ctaLabel: site.ctaStrategy.footer.label, ctaUrl: site.ctaStrategy.footer.href, eventType: "contact_click" })`
    - Add section exposure tracking using IntersectionObserver:
      ```typescript
      useEffect(() => {
        const observer = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                const sectionId = entry.target.getAttribute("data-section-id");
                analyticsEmitter.track({
                  eventType: "section_exposure",
                  eventName: "Section viewed",
                  siteId: site.id,
                  leadId: site.leadId,
                  metadata: { sectionId, percentVisible: Math.round(entry.intersectionRatio * 100) },
                });
              }
            });
          },
          { threshold: 0.5 } // Trigger when 50% visible
        );
        document.querySelectorAll("[data-section-id]").forEach((el) => observer.observe(el));
        return () => observer.disconnect();
      }, [site]);
      ```
    - Add `data-section-id` attributes to section elements in the render function
    - File: `apps/web/src/components/site-workspace-controls.tsx`
    - Add admin event tracking:
      - After generate: `trackSiteGenerated({ siteId, themeKey, variantKey })`
      - After override: `trackSiteOverrideApplied({ siteId, path, scope })`
      - After export: `trackSiteExportCreated({ siteId, exportType })`
    - File: `apps/web/src/app/nsa/messages/[id]/page.tsx`
    - Add messaging event tracking:
      - On draft edit: `trackMessageDraftEdited({ messageId, channel })`
      - On mark ready: `trackMessageMarkedReady({ messageId, channel })`
    - File: `apps/web/src/app/nsa/leads/page.tsx`
    - Add lead event tracking:
      - On lead import: `trackLeadImported({ leadId, sourceType })`
      - On lead create: `trackLeadCreated({ leadId })`
  - **What already exists:**
    - Some CTA tracking exists in preview page (lines 196, 204, 355 in sites/[slug]/page.tsx)
    - Analytics event types are defined in backend schema
    - Shared emitter will be created from previous task
  - **What needs to be done:**
    - Add CTA click tracking for all CTAs in preview
    - Add IntersectionObserver for section exposure tracking
    - Add admin event tracking in site workspace controls
    - Add messaging event tracking in message workspace
    - Add lead event tracking in lead management
    - Ensure all event types from taxonomy are covered

- [ ] Automated regression tests for `/api/analytics/events` and aggregation accuracy.
  - **Backend changes needed:**
    - File: `apps/backend/tests/test_analytics.py` (create if doesn't exist)
    - Add test class `TestAnalyticsIngestion`:
      - `test_ingest_single_event()` - test that a single event is persisted correctly
      - `test_ingest_batch_events()` - test that multiple events are persisted
      - `test_event_validation()` - test that invalid events are rejected
      - `test_session_tracking()` - test that sessionId is correctly stored
      - `test_site_lead_association()` - test that siteId and leadId are correctly linked
    - Add test class `TestAnalyticsAggregation`:
      - `test_dashboard_summary()` - test that summary metrics are correctly aggregated
      - `test_site_metrics_aggregation()` - test per-site metrics accuracy
      - `test_lead_metrics_aggregation()` - test per-lead metrics accuracy
      - `test_variant_metrics_aggregation()` - test per-variant metrics accuracy
      - `test_message_metrics_aggregation()` - test per-message metrics accuracy
      - `test_cta_click_counting()` - test that CTA clicks are correctly counted by type
      - `test_unique_session_counting()` - test that unique sessions are correctly deduplicated
    - Add test class `TestAnalyticsRetention`:
      - `test_event_retention()` - test that events are retained for correct duration
      - `test_event_purge()` - test that old events are purged after TTL
    - Add test class `TestAnalyticsEdgeCases`:
      - `test_missing_optional_fields()` - test that events with missing optional fields are handled
      - `test_malformed_metadata()` - test that malformed metadata doesn't break aggregation
      - `test_concurrent_ingestion()` - test that concurrent event ingestion is handled correctly
    - File: `apps/backend/tests/conftest.py`
    - Add fixtures for analytics testing:
      - `analytics_event_factory()` - factory for creating test events
      - `sample_site_metrics()` - sample site metrics for testing
      - `sample_dashboard_response()` - sample dashboard response for testing
  - **What already exists:**
    - Analytics repository exists in `app/core/analytics.py`
    - Analytics API endpoints exist in `app/api/analytics.py`
    - Test infrastructure exists with `conftest.py`
  - **What needs to be done:**
    - Create comprehensive test suite for analytics ingestion
    - Create comprehensive test suite for analytics aggregation
    - Add tests for retention and edge cases
    - Add test fixtures for analytics data
    - Ensure tests cover all aggregation logic paths
    - Add tests for accuracy of metric calculations
