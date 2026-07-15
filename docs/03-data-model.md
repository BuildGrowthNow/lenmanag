# Data Model

## Core Collections

### users

Internal authenticated users.

Important fields:

- `_id`
- `email`
- `name`
- `role`
- `status`
- `createdAt`
- `lastLoginAt`

### auth_allowlist

Approved email addresses allowed to access the master system.

Important fields:

- `_id`
- `email`
- `enabled`
- `notes`
- `createdAt`
- `updatedAt`

### leads

Represents an imported prospect or company.

Important fields:

- `_id`
- `sourceType` (`csv`, `manual`, `crm`, future)
- `sourceRef`
- `companyName`
- `websiteUrl`
- `detectedWebsiteUrl`
- `status`
- `industry`
- `notes`
- `createdAt`
- `updatedAt`

### site_extractions

Stores the raw and normalized crawl result for a lead website.

Important fields:

- `_id`
- `leadId`
- `crawlStatus`
- `sitemapStatus`
- `pagesDiscovered`
- `pagesCrawled`
- `homepageHtmlSummary`
- `sitemapUrls`
- `brandSignals`
- `contentBlocks`
- `ctaInventory`
- `seoMetadata`
- `mediaAssets`
- `rawSnapshots`
- `sourceMap`
- `contentConfidence`
- `missingSignals`
- `gapItems`
- `placeholderRisk`
- `createdAt`
- `updatedAt`

### site_briefs

Stores the interpreted design and messaging brief derived from extracted public content.

Important fields:

- `_id`
- `leadId`
- `sourceExtractionId`
- `companySummary`
- `audienceHypotheses`
- `valueProposition`
- `brandSummary`
- `toneProfile`
- `conversionAngle`
- `recommendedHero`
- `recommendedSections`
- `proofPoints`
- `sourceCitations`
- `confidenceScore`
- `missingRequirements`
- `needsReview`
- `version`
- `createdAt`
- `updatedAt`

### generated_sites

Represents the redesign output.

Important fields:

- `_id`
- `leadId`
- `themeId`
- `themeKey`
- `brandTokens`
- `sections`
- `heroVariant`
- `ctaStrategy`
- `conversionAngle`
- `designRationale`
- `qualityScore`
- `readinessStatus`
- `missingRequirements`
- `qaNotes`
- `previewSlug`
- `renderStatus`
- `publishedAt`
- `createdAt`
- `updatedAt`

### site_overrides

Stores manual operator edits that should survive regeneration.

Important fields:

- `_id`
- `leadId`
- `generatedSiteId`
- `scope` (`copy`, `layout`, `brand`, `cta`, `motion`, `style`)
- `path`
- `value`
- `previousValue`
- `reason`
- `sourceType` (`manual`, `imported`, `regenerated`)
- `status`
- `createdBy`
- `createdAt`
- `updatedAt`

### site_exports

Tracks exported snapshots and handoff artifacts for local work or GitHub sync.

Important fields:

- `_id`
- `leadId`
- `generatedSiteId`
- `exportType` (`local_bundle`, `github_repo`, `zip`, future)
- `repoUrl`
- `branch`
- `commitSha`
- `exportPath`
- `status`
- `notes`
- `createdAt`
- `updatedAt`

### messaging_drafts

Stores outreach copy suggestions.

Important fields:

- `_id`
- `leadId`
- `channel`
- `subject`
- `body`
- `tone`
- `angle`
- `status`
- `version`
- `createdAt`
- `updatedAt`

### analytics_events

Stores product and preview analytics.

Important fields:

- `_id`
- `siteId`
- `leadId`
- `sessionId`
- `visitorFingerprint`
- `eventType`
- `eventName`
- `pagePath`
- `referrer`
- `utm`
- `metadata`
- `createdAt`

### jobs

Tracks background processing.

Important fields:

- `_id`
- `leadId`
- `jobType`
- `status`
- `progress`
- `step`
- `errorMessage`
- `startedAt`
- `finishedAt`
- `createdAt`
- `updatedAt`

### theme_variants

Defines reusable design directions that the generator can choose from.

Important fields:

- `_id`
- `themeKey`
- `name`
- `heroFamily`
- `sectionStack`
- `motionPreset`
- `typographyPairing`
- `spacingStyle`
- `colorTreatment`
- `bestForIndustries`
- `placeholderPolicy`
- `allowedPaletteModes`
- `createdAt`
- `updatedAt`

### audit_logs

Tracks changes made by internal users or automation.

Important fields:

- `_id`
- `actorUserId`
- `entityType`
- `entityId`
- `action`
- `before`
- `after`
- `createdAt`

## Relationships

- One user can manage many leads.
- One lead can have many extraction snapshots over time.
- One lead can have many site briefs over time.
- One lead can have many generated site versions.
- One lead can have many override records.
- One lead can have many exports or snapshots.
- One lead can have many messaging drafts.
- One site can have many analytics events.
- One lead can have many jobs.
- One theme variant can be reused across many generated sites.

## Important Modeling Rules

- Keep lead identity separate from extraction output.
- Keep extraction output separate from interpreted site briefs.
- Keep generated design data separate from raw crawl data.
- Keep analytics append-only.
- Keep audit logs immutable.
- Version generated content rather than overwriting it whenever possible.
- Store operator edits as override records so regenerated output preserves manual changes.
- Treat exports as snapshots or handoff artifacts, not as the source of truth.
- Keep missing source information as explicit gaps rather than filling them with placeholder copy or fake visuals.
- Keep public previews free of lorem ipsum, demo images, fake testimonials, invented metrics, and other non-production fillers.

## Brand Token Model

The brand token object should include:

- primary color
- secondary color
- accent color
- background color
- text color
- border color
- logo asset reference
- font recommendation
- visual tone
- motion intensity
- layout density
- audience fit notes
- placeholder policy
- missing-field guidance

Those tokens drive the preview design system.

## Implementation status

**Checklist**

- [x] Pydantic schemas exist for the major collections (see `apps/backend/app/schemas/*`).
- [x] Lead, extraction, brief, site, and messaging repositories operate on the documented shapes (`app/core/leads.py`, `app/core/extraction.py`, `app/core/sites.py`, `app/core/messages.py`).
- [x] Mongo persistence is optional; several repositories still fall back to in-memory storage when the database URI is missing, so collection-level behaviors (indexes, uniqueness) aren’t enforced yet.
- [x] Override/export collections are defined here but not implemented anywhere in the backend or UI.
- [x] Analytics events are modeled but no ingestion endpoints or retention policies exist.

**Details**

The implemented schemas and repositories closely follow this document, so developers work with consistent objects across the stack. We now spin up a Mongo-compatible store even when no external URI is present (via an asynchronous mongomock client), so the repositories always create indexes and enforce uniqueness. Site overrides and export metadata are persisted through dedicated collections, surfaced via the admin UI (including disable/history actions), and replayed into each regeneration. Analytics ingestion endpoints are live, wired to preview instrumentation and admin workflows, and automatically prune historical events after 45 days to keep the dataset lean without losing recent context.
