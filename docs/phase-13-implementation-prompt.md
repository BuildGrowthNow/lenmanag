# Phase 13 Implementation Prompt: Asset Capture and Preview Guardrails

## Overview

Phase 13 focuses on Asset Capture and Preview Guardrails - implementing a reliable asset download and caching system, enforcing crawl budget limits, and ensuring CTAs and copy remain client-facing without exposing internal operator language.

## Context

Refer to `docs/12-asset-capture-and-preview-guardrails.md` for the complete specification. The goal is to ensure previews remain stable even if source sites block hot-linking, implement traceable retention policies, add smarter crawl coverage with safety limits, and maintain client-safe copy in generated previews.

## Current State

**What already exists:**
- Extraction snapshot schema with `brandAssetCues` field containing sourceUrl, assetType, value, confidence
- `crawl_website()` function in `extraction.py` that discovers images, logos, fonts
- Config system in `app/core/config.py` with environment variable support
- Celery app exists in `app/core/celery_app.py`
- Analytics repository exists with dashboard aggregation
- MongoDB TTL indexes can be used for automatic expiration
- `_hero_variant()`, `_cta_strategy()`, and `_section_stack()` functions in `sites.py` generate CTAs and content

**What needs to be done:**
- Implement asset downloader service with MIME validation and byte limits
- Add storage backend abstraction (local disk or S3)
- Integrate downloader into extraction pipeline
- Add retention jobs and monitoring metrics
- Increase MAX_PAGES and add crawl budget enforcement
- Update generator CTA helper and section templates for client-safe phrasing
- Expose new settings in admin config UI

## Implementation Tasks

### Task 1: Implement Downloader Service + Storage Wiring

**Backend:**
- File: `apps/backend/app/core/asset_downloader.py` (new file)
  - Create `AssetDownloader` class with methods:
    - `download_asset(url: str, lead_id: str) -> AssetDownloadResult` - downloads single asset with MIME validation
    - `download_batch(urls: list[str], lead_id: str) -> list[AssetDownloadResult] - downloads multiple assets concurrently (max 3)
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

**Frontend:**
- No frontend changes for this task

### Task 2: Update Extraction Snapshot Schema

**Backend:**
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

**Frontend:**
- File: `apps/web/src/app/nsa/leads/[id]/extraction/page.tsx`
  - Display crawl budget usage (e.g., "8.2MB / 12MB used")
  - Show asset cache stats (e.g., "12 images, 3 fonts cached")
  - Display TTL for cached assets
  - Add warning if crawl budget was exceeded

### Task 3: Add Retention Jobs + Monitoring Metrics

**Backend:**
- File: `apps/backend/app/core/asset_retention.py` (new file)
  - Create `AssetRetentionManager` class with methods:
    - `purge_expired_assets() -> PurgeResult` - deletes assets past TTL
    - `get_storage_stats() -> StorageStats` - returns total bytes, file count, by-type breakdown
    - `pin_assets(lead_id: str) -> None` - marks assets for active project (extends TTL)
    - `unpin_assets(lead_id: str) -> None` - removes pin, returns to default TTL

- File: `apps/backend/app/core/tasks.py`
  - Add Celery task: `@celery_app.task(name="purge_expired_assets")` - runs daily to purge expired assets

- File: `apps/backend/app/core/analytics.py`
  - Add asset retention metrics to dashboard:
    - `totalAssetBytesStored: int`
    - `assetPurgeCount: int` (last 24h)
    - `assetDownloadFailures: int` (last 24h)
    - `assetCacheHitRate: float` (cached vs. source requests)

- File: `apps/backend/app/api/analytics.py`
  - Add endpoint `GET /api/analytics/assets` for asset-specific metrics

**Frontend:**
- File: `apps/web/src/app/nsa/analytics/page.tsx` (or existing analytics page)
  - Display asset storage metrics
  - Show purge counts and download failures
  - Display cache hit rate

### Task 4: Raise MAX_PAGES, Add Budget Enforcement

**Backend:**
- File: `apps/backend/app/core/extraction.py`
  - Change `MAX_PAGES` from 6 to 10
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

**Frontend:**
- File: `apps/web/src/app/nsa/leads/[id]/extraction/page.tsx`
  - Display crawl budget usage (e.g., "2.1MB / 3MB HTML budget used")
  - Display time elapsed (e.g., "38s / 45s time budget used")
  - Show prioritization order in page inventory (label each page source: homepage, sitemap, internal_link)
  - Add warning if crawl was truncated due to budget

### Task 5: Update Generator CTA Helper + Section Templates

**Backend:**
- File: `apps/backend/app/core/sites.py`
  - Add `_is_client_safe_cta(text: str) -> bool` function that:
    - Checks against whitelist of allowed CTA verbs: Book, Schedule, Request, Explore, Contact, Learn, Discover, Get, Start
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

**Test:**
- File: `apps/backend/tests/test_cta_safety.py` (new file)
  - Add unit tests for `_is_client_safe_cta()`:
    - Test allowed verbs pass
    - Test blocked phrases fail
    - Test case-insensitive matching
  - Add integration tests for generation with blocked language:
    - Test that generation fails when brief contains blocked phrases
    - Test that generation succeeds with client-safe alternatives

**Frontend:**
- No frontend changes for this task

### Task 6: Expose New Settings in Admin Config

**Backend:**
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

**Frontend:**
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

## Code Quality Standards

- Follow existing patterns in `apps/backend/app/core/extraction.py` and `apps/backend/app/core/sites.py`
- Use existing UI components from `apps/web/src/components/ui/`
- Maintain type safety in TypeScript with proper interface definitions
- Add proper error handling and user-friendly error messages
- Include loading states for async operations
- Add validation for user inputs (URLs, character limits, required fields)
- Ensure no code duplication - extract reusable components where appropriate
- Write production-ready code with proper logging and audit trails
- Use feature flags for new functionality to enable gradual rollout

## Testing Requirements

- Write unit tests for asset downloader in `apps/backend/tests/test_asset_downloader.py`
- Write unit tests for retention manager in `apps/backend/tests/test_asset_retention.py`
- Write unit tests for CTA safety in `apps/backend/tests/test_cta_safety.py`
- Test MIME validation with various content types
- Test byte limit enforcement with large files
- Test crawl budget truncation scenarios
- Test CTA validation with allowed and blocked phrases
- Test config API endpoints with admin authentication
- Verify settings UI validation and error handling
- Test retention job execution and asset purging

## Success Criteria

- Assets are downloaded and cached with proper MIME validation
- Byte limits are enforced per-file and per-crawl
- Crawl budget stops crawls before exceeding limits
- Retention jobs purge expired assets automatically
- CTAs and copy never expose internal operator language
- Settings can be updated via admin UI without redeployment
- All changes integrate seamlessly with existing extraction pipeline
