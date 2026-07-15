# Asset Capture and Preview Guardrails

## Purpose

Define the next set of engineering tasks so operators can reliably reuse a lead's public imagery, keep crawls lightweight, and ensure previews only show client-facing content.

This phase covers:

- downloading and short-term caching of public assets
- retention and deletion policies for crawled artifacts
- crawler depth adjustments and safety limits
- CTA/content rules so previews never expose operator notes

## Goals

1. **Stable media** — previews should keep working even if the source site blocks hot-linking or removes assets later.
2. **Traceable retention** — every downloaded artifact has a known size, storage location, and expiry policy.
3. **Smarter crawl coverage** — up to ten priority pages per site without runaway timeouts or bandwidth spikes.
4. **Client-safe copy** — generated CTAs and section text remain customer-facing; internal caveats stay in the admin surface.

## Asset Downloader Requirements

- Only run against assets discovered during extraction (no arbitrary URL injection).
- Enforce a MIME allowlist: `image/*`, `font/*`, optional `text/css` for critical stylesheets.
- Per-file byte ceiling (recommended: 1.5 MB) and per-crawl aggregate cap (recommended: 12 MB) with graceful skips when exceeded.
- Limit concurrent downloads (e.g., 3 at a time) and respect a short timeout (≤5 s per asset).
- Store binaries in a managed bucket (local temp, S3, etc.) with metadata: `sourceUrl`, `checksum`, `mimeType`, `bytes`, `capturedAt`, `expiresAt`.
- Persist only the internal asset URI inside `brandAssetCues` so renderers never hot-link the lead's origin directly.
- Honor obvious exclusion signals (`robots.txt`, `Cache-Control: no-store`, or explicit operator blocklist) and skip downloads when the response is disallowed.

## Retention & Cleanup

- Default TTL: delete asset binaries and extraction snapshots 7 days after capture unless the operator marks the lead as "pinned" for an active project.
- Use TTL indexes (Mongo) plus a storage lifecycle rule (bucket auto-expire) to guarantee consistency.
- Provide an audit entry whenever an asset is purged or pinned.
- Ensure exports & handoff bundles explicitly copy only the assets they need; no shared bucket references after export.

## Crawl Depth & Budget

- Increase `MAX_PAGES` from 6 → 10 but keep:
  - homepage always first
  - sitemap-listed pages next (respect declared priority when present)
  - navigation/internal links last, deduped by canonical URL
- Introduce a **crawl budget**: stop early if total downloaded HTML exceeds 3 MB or more than 45 seconds elapse.
- Record `crawlBudgetUsed` in the snapshot so operators see whether the site was truncated.

## CTA & Copy Policy

- Public previews must never surface operator-only language ("review the preview", "see source notes", "traceability", etc.).
- Maintain a whitelist of CTA verbs (e.g., Book, Schedule, Request, Explore, Contact) and block internal phrases automatically.
- Section body text should describe the client's offering; rationale or inference labels belong in metadata (used by the admin UI) rather than front-facing copy.
- Add validation in the generator to fail a build if disallowed phrases slip through, forcing the operator to fix the brief/overrides.

## Delivery Checklist

- [ ] Implement downloader service + storage wiring with feature flag so we can test per-tenant.
  - **Backend changes needed:**
    - File: `apps/backend/app/core/asset_downloader.py` (new file)
    - Create a new class `AssetDownloader` with methods:
      - `download_asset(url: str, lead_id: str) -> AssetDownloadResult` - downloads a single asset with MIME validation
      - `download_batch(urls: list[str], lead_id: str) -> list[AssetDownloadResult]` - downloads multiple assets concurrently (max 3 at a time)
      - `validate_mime_type(content_type: str) -> bool` - checks against allowlist (image/*, font/*, text/css)
      - `enforce_byte_limit(content: bytes, max_bytes: int = 1_500_000) -> bool` - enforces 1.5MB per-file limit
      - `enforce_aggregate_limit(total_bytes: int, max_bytes: int = 12_000_000) -> bool` - enforces 12MB per-crawl limit
    - Add dependency on `aiohttp` or `httpx` for async downloads in `apps/backend/pyproject.toml`
    - Add storage backend abstraction (S3 via `boto3` or local disk via `pathlib`)
    - File: `apps/backend/app/core/config.py`
    - Add new config settings:
      - `ASSET_DOWNLOAD_ENABLED: bool = False` (feature flag)
      - `ASSET_STORAGE_BACKEND: str = "local"` (local or s3)
      - `ASSET_MAX_FILE_BYTES: int = 1_500_000`
      - `ASSET_MAX_AGGREGATE_BYTES: int = 12_000_000`
      - `ASSET_DOWNLOAD_TIMEOUT: int = 5`
      - `ASSET_CONCURRENT_DOWNLOADS: int = 3`
      - `ASSET_S3_BUCKET: str | None = None`
      - `ASSET_LOCAL_PATH: str = "/tmp/lenquant_assets"`
    - File: `apps/backend/app/core/extraction.py`
    - Modify `crawl_website()` to call `AssetDownloader.download_batch()` for discovered assets
    - Store downloaded asset URIs in `brandAssetCues` (replace source URLs with cached URIs)
    - Add crawl budget tracking: `crawlBudgetUsed: int` and `crawlBudgetLimit: int`
  - **What already exists:**
    - `ExtractionSnapshot` schema has `brandAssetCues` field with sourceUrl, assetType, value
    - `crawl_website()` function in `extraction.py` already discovers images, logos, fonts
    - Config system exists in `app/core/config.py`
  - **What needs to be done:**
    - Create asset downloader service with validation
    - Add storage backend abstraction
    - Integrate downloader into extraction pipeline
    - Add feature flag and config settings
    - Replace source URLs with cached asset URIs
    - Add error handling for download failures

- [ ] Update extraction snapshot schema to reference cached assets, record TTL metadata, and surface crawl budget.
  - **Backend changes needed:**
    - File: `apps/backend/app/schemas/extraction.py`
    - Extend `BrandAssetCue` schema to include:
      - `cachedUri: str | None` - internal asset URI after download
      - `cachedAt: datetime | None` - when asset was cached
      - `expiresAt: datetime | None` - when asset will be purged
      - `bytes: int | None` - asset size in bytes
      - `checksum: str | None` - SHA-256 hash for integrity
    - Extend `ExtractionSnapshot` schema to include:
      - `crawlBudgetUsed: int` - total bytes downloaded in this crawl
      - `crawlBudgetLimit: int` - max bytes allowed (default 12MB)
      - `crawlTimeElapsedSeconds: int | None` - time spent crawling
      - `assetCacheStats: dict[str, int]` - count of cached assets by type (image, font, css)
      - `assetRetentionDays: int = 7` - TTL for cached assets
    - File: `apps/backend/app/core/extraction.py`
    - Modify `_extract_brand_asset_cues()` to populate the new cached asset fields
    - Add crawl budget tracking in `crawl_website()`:
      - Track total bytes downloaded
      - Stop early if budget exceeded
      - Record time elapsed
    - File: `apps/backend/app/core/sites.py`
    - Update `_brand_tokens()` to use `cachedUri` instead of `sourceUrl` when available
    - Update `_site_refs()` to reference cached asset URIs
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/leads/[id]/extraction/page.tsx`
    - Display crawl budget usage (e.g., "8.2MB / 12MB used")
    - Show asset cache stats (e.g., "12 images, 3 fonts cached")
    - Display TTL for cached assets
    - Add warning if crawl budget was exceeded
  - **What already exists:**
    - `BrandAssetCue` schema exists with sourceUrl, assetType, value, confidence
    - `ExtractionSnapshot` schema exists with pageInventory, sourceCitations, brandAssetCues
    - Extraction page UI exists showing crawl status
  - **What needs to be done:**
    - Extend schemas with cache metadata
    - Add crawl budget tracking
    - Update token generation to use cached URIs
    - Surface cache stats in extraction UI

- [ ] Add retention jobs + monitoring metrics (bytes stored, purge counts, failures).
  - **Backend changes needed:**
    - File: `apps/backend/app/core/asset_retention.py` (new file)
    - Create a new class `AssetRetentionManager` with methods:
      - `purge_expired_assets() -> PurgeResult` - deletes assets past TTL
      - `get_storage_stats() -> StorageStats` - returns total bytes, file count, by-type breakdown
      - `pin_assets(lead_id: str) -> None` - marks assets for active project (extends TTL)
      - `unpin_assets(lead_id: str) -> None` - removes pin, returns to default TTL
    - Add a Celery task in `apps/backend/app/core/tasks.py`:
      - `@celery_app.task(name="purge_expired_assets")` - runs daily to purge expired assets
    - File: `apps/backend/app/core/analytics.py`
    - Add asset retention metrics to dashboard:
      - `totalAssetBytesStored: int`
      - `assetPurgeCount: int` (last 24h)
      - `assetDownloadFailures: int` (last 24h)
      - `assetCacheHitRate: float` (cached vs. source requests)
    - File: `apps/backend/app/api/analytics.py`
    - Add endpoint `GET /api/analytics/assets` for asset-specific metrics
  - **What already exists:**
    - Celery app exists in `app/core/celery_app.py`
    - Analytics repository exists with dashboard aggregation
    - MongoDB TTL indexes can be used for automatic expiration
  - **What needs to be done:**
    - Create retention manager class
    - Add Celery task for daily purges
    - Add asset metrics to analytics dashboard
    - Implement pin/unpin functionality for active projects
    - Add monitoring for download failures

- [ ] Raise `MAX_PAGES`, add budget enforcement, and document the prioritization order.
  - **Backend changes needed:**
    - File: `apps/backend/app/core/extraction.py`
    - Change `MAX_PAGES` from 6 to 10 (line 15)
    - Add budget enforcement in `crawl_website()`:
      - Before fetching each page, check if `total_bytes + estimated_page_size > CRAWL_BUDGET_BYTES`
      - If budget exceeded, stop crawling and mark crawl as `partial`
      - Track `crawlBudgetUsed` in the snapshot
    - Add time budget enforcement:
      - Track elapsed time since crawl start
      - Stop if `elapsed_seconds > CRAWL_TIME_LIMIT_SECONDS` (default 45)
      - Record `crawlTimeElapsedSeconds` in snapshot
    - Document prioritization order in code comments:
      1. Homepage (always first)
      2. Sitemap-listed pages (respect priority if available)
      3. Navigation/internal links (deduped by canonical URL)
    - File: `apps/backend/app/core/config.py`
    - Add config settings:
      - `CRAWL_MAX_PAGES: int = 10`
      - `CRAWL_BUDGET_BYTES: int = 3_000_000` (3MB HTML limit)
      - `CRAWL_TIME_LIMIT_SECONDS: int = 45`
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/leads/[id]/extraction/page.tsx`
    - Display crawl budget usage (e.g., "2.1MB / 3MB HTML budget used")
    - Display time elapsed (e.g., "38s / 45s time budget used")
    - Show prioritization order in page inventory (label each page source: homepage, sitemap, internal_link)
    - Add warning if crawl was truncated due to budget
  - **What already exists:**
    - `MAX_PAGES` constant exists in `extraction.py`
    - Page prioritization logic exists (homepage first, then sitemap, then internal links)
    - Extraction snapshot has `pagesCrawled` and `pagesDiscovered` fields
  - **What needs to be done:**
    - Increase MAX_PAGES to 10
    - Add byte budget enforcement (3MB HTML limit)
    - Add time budget enforcement (45s limit)
    - Document prioritization order
    - Surface budget metrics in extraction UI
    - Add truncation warnings

- [ ] Update generator CTA helper + section templates to use client-safe phrasing only; add unit tests for blocked language.
  - **Backend changes needed:**
    - File: `apps/backend/app/core/sites.py`
    - Add a new function `_is_client_safe_cta(text: str) -> bool` that:
      - Checks against a whitelist of allowed CTA verbs: Book, Schedule, Request, Explore, Contact, Learn, Discover, Get, Start
      - Blocks internal phrases: "review the preview", "see source notes", "traceability", "operator", "admin", "internal"
      - Returns False if blocked phrase detected
    - Modify `_hero_variant()` to use client-safe CTAs:
      - Replace "Review the preview" with "Explore the preview" or "View the site"
      - Replace "See source notes" with "Learn more" or "Discover"
    - Modify `_cta_strategy()` to use client-safe CTAs:
      - Replace "See the source notes" with "Learn more"
      - Replace "Review the brief" with "Get started"
    - Modify `_section_stack()` to ensure section body text is client-safe:
      - Add validation in section generation to check for blocked phrases
      - If blocked phrase found, replace with generic client-safe alternative or mark as gap
    - Add validation in `site_repository.generate_site()`:
      - After generation, check all CTAs and section text for blocked language
      - If blocked language found, raise ValueError with details
      - This forces operator to fix the brief/overrides before proceeding
  - **Test changes needed:**
    - File: `apps/backend/tests/test_cta_safety.py` (new file)
    - Add unit tests for `_is_client_safe_cta()`:
      - Test allowed verbs pass
      - Test blocked phrases fail
      - Test case-insensitive matching
    - Add integration tests for generation with blocked language:
      - Test that generation fails when brief contains blocked phrases
      - Test that generation succeeds with client-safe alternatives
  - **What already exists:**
    - `_hero_variant()` function generates hero CTAs (lines 435-469)
    - `_cta_strategy()` function generates CTA strategy (lines 553-574)
    - `_section_stack()` function generates section content (lines 472-550)
  - **What needs to be done:**
    - Create client-safe CTA validation function
    - Update hero and CTA generation to use safe phrasing
    - Add validation to section generation
    - Add generation-time validation that fails on blocked language
    - Write comprehensive unit tests for CTA safety

- [ ] Expose new settings (TTL days, byte caps, CTA whitelist) in the admin config so ops can tweak without redeploying.
  - **Backend changes needed:**
    - File: `apps/backend/app/core/config.py`
    - Ensure all new settings are environment-variable backed:
      - `ASSET_RETENTION_DAYS: int = int(os.getenv("ASSET_RETENTION_DAYS", "7"))`
      - `ASSET_MAX_FILE_BYTES: int = int(os.getenv("ASSET_MAX_FILE_BYTES", "1500000"))`
      - `ASSET_MAX_AGGREGATE_BYTES: int = int(os.getenv("ASSET_MAX_AGGREGATE_BYTES", "12000000"))`
      - `CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "10"))`
      - `CRAWL_BUDGET_BYTES: int = int(os.getenv("CRAWL_BUDGET_BYTES", "3000000"))`
      - `CRAWL_TIME_LIMIT_SECONDS: int = int(os.getenv("CRAWL_TIME_LIMIT_SECONDS", "45"))`
      - `CTA_ALLOWED_VERBS: str = os.getenv("CTA_ALLOWED_VERBS", "Book,Schedule,Request,Explore,Contact,Learn,Discover,Get,Start")`
      - `CTA_BLOCKED_PHRASES: str = os.getenv("CTA_BLOCKED_PHRASES", "review the preview,see source notes,traceability,operator,admin,internal")`
    - File: `apps/backend/app/api/config.py` (new file or extend existing)
    - Add endpoint `GET /api/config` that returns current config values (excluding secrets)
    - Add endpoint `PATCH /api/config` to update runtime config (requires admin role)
  - **Frontend changes needed:**
    - File: `apps/web/src/app/nsa/settings/page.tsx` (create if doesn't exist)
    - Create a settings page with sections:
      - "Asset Retention" - TTL days, byte caps
      - "Crawl Budget" - max pages, byte budget, time limit
      - "CTA Safety" - allowed verbs, blocked phrases
    - Each setting should have:
      - Current value display
      - Input field to change value
      - Save button that calls PATCH /api/config
      - Reset to default button
    - Add validation for numeric inputs
    - Add warning when changing critical settings (e.g., "This will affect all future crawls")
  - **What already exists:**
    - Config system exists in `app/core/config.py` with environment variable support
    - Admin authentication exists via session cookies
  - **What needs to be done:**
    - Ensure all new settings are environment-variable backed
    - Create config API endpoints for get/patch
    - Build admin settings UI page
    - Add validation and warnings for setting changes

## Open Questions

- Should we watermark cached images when exported to prevent inadvertent reuse outside the engagement?
- Do we need explicit customer consent before caching assets, or is public content sufficient under current contracts?
- Which storage backend (local disk vs. cloud bucket) best matches our deployment topology and cost profile?
