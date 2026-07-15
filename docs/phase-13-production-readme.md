# Phase 13 — Production Readme: Asset Capture & Preview Guardrails

This document describes environment variables, GCP setup, IAM least-privilege, CI setup, integration test instructions, and Mongo index migration notes for the asset capture and preview guardrails implemented in Phase 13.

## Environment variables
- `ASSET_STORAGE_BACKEND` = "gcp" | "local" (default: `local`)
- `ASSET_GCP_BUCKET` – target GCS bucket name (required when `ASSET_STORAGE_BACKEND=gcp`)
- `ASSET_GCP_PROJECT` – optional GCP project id
- `GCP_SERVICE_ACCOUNT_KEY` – service account JSON (either as path or JSON string)
- `ASSET_MAX_FILE_BYTES` – per-file maximum in bytes (int)
- `ASSET_MAX_AGGREGATE_BYTES` – per-crawl aggregate byte limit (int)
- `ASSET_RETENTION_DAYS` – days to retain cached assets
- `ASSET_GCP_SIGNED_URL_EXPIRY` – default signed URL expiry in seconds
- `ASSET_CONCURRENT_DOWNLOADS` – concurrent downloader worker limit
- `ASSET_DOWNLOAD_TIMEOUT` – network timeout seconds for downloads

Other related settings live in `apps/backend/app/core/config.py` and are loaded from env (or `.env`).

## GCP Service Account and IAM (least-privilege)
1. Create a service account for the asset caching service:

   ```bash
   gcloud iam service-accounts create lenquant-asset-uploader --display-name "LenQuant Asset Uploader"
   ```

2. Grant least privilege roles on the target bucket (replace `my-bucket`):

   ```bash
   # On the bucket grant Storage Object Admin for upload/delete
   gsutil iam ch serviceAccount:LENQUANT_SA_EMAIL:roles/storage.objectAdmin gs://my-bucket
   ```

   Recommended minimal role for full lifecycle (upload/delete): `roles/storage.objectAdmin`.
   For read-only access (if applicable), use `roles/storage.objectViewer`.

3. Export the service account key (or store it in Secret Manager / CI secrets):

   ```bash
   gcloud iam service-accounts keys create key.json --iam-account=LENQUANT_SA_EMAIL
   ```

   - Do NOT commit `key.json` to source control. Store it in CI secrets or Secret Manager and inject via env `GCP_SERVICE_ACCOUNT_KEY`.

## CI integration & secrets
- GitHub Actions workflow `.github/workflows/ci.yml` runs unit tests on push/PR.
- Integration tests are gated and only run when `GCP_SERVICE_ACCOUNT_KEY` (and optionally `ASSET_GCP_BUCKET`) are present as repository secrets.
- Set `GCP_SERVICE_ACCOUNT_KEY` secret to the JSON content of the service account key (string escaped). Optionally set `ASSET_GCP_BUCKET` to the test bucket name.

## Running tests locally
- Unit tests:

  ```bash
  cd apps/backend
  pytest -q
  ```

- Integration tests (real GCS bucket required):

  ```bash
  export GCP_SERVICE_ACCOUNT_KEY='{"type": ... }'  # service account JSON string
  export ASSET_STORAGE_BACKEND=gcp
  export ASSET_GCP_BUCKET=my-test-bucket
  cd apps/backend
  pytest tests/integration/test_gcs_upload.py -q
  ```

  The integration test creates objects under a unique prefix and attempts to clean up after itself.

## Mongo index migration note
The asset metadata collection `asset_metadata` uses:
- TTL index on `expiresAt` to let Mongo automatically expire documents: `db.asset_metadata.createIndex({expiresAt:1}, {expireAfterSeconds: 0})`
- Index on `leadId`: `db.asset_metadata.createIndex({leadId:1})`

The code attempts to create these indexes on startup via `asset_metadata.create_indexes()`.
If you prefer to create indexes manually, run the mongo shell commands above against the target DB.

## Runbook & operational notes
- Logs are structured with correlation ids (crawl ids) where possible. Use those ids to trace asset lifecycle.
- If switching to GCP backend, ensure `GCP_SERVICE_ACCOUNT_KEY` is available and `ASSET_GCP_BUCKET` points to the target bucket.
- If you require stronger atomicity for crawl budgets, enable MongoDB replica set and switch to multi-document transactions. The current implementation uses optimistic upsert with rollback on over-commit — documented tradeoff.
- For long-running crawls, monitor Prometheus metrics exposed at `/api/v1/metrics`:
  - `asset_download_total`
  - `asset_download_failures_total`
  - `asset_download_bytes_total`
  - `asset_download_latency_seconds`
  - `asset_purge_count`
  - `asset_purge_bytes`

## Troubleshooting
- Missing GCP creds: services will raise a clear runtime error indicating `GCP_SERVICE_ACCOUNT_KEY` or `ASSET_GCP_BUCKET` is required.
- If integration tests fail due to permissions, ensure the service account has `roles/storage.objectAdmin` on the bucket.

## Next steps / Hardening suggestions
- Rotate service account keys regularly and prefer Secret Manager for production deployments.
- Add RBAC for admin roles beyond the allowlist email approach.
- Add end-to-end monitoring dashboards for purge/ingest rates and storage costs.

***
