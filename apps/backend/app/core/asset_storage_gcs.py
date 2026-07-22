from __future__ import annotations

import json
import uuid
from datetime import timedelta
from typing import BinaryIO, Dict, Tuple

from google.cloud import storage  # type: ignore[attr-defined]
from google.oauth2 import service_account
from google.api_core import retry as gcloud_retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

from .config import get_settings

settings = get_settings()


class GCSAssetStorage:
    def __init__(self):
        if not settings.asset_gcp_bucket:
            raise RuntimeError("ASSET_GCP_BUCKET is required for GCSAssetStorage")

        self.bucket_name = settings.asset_gcp_bucket
        self.client = self._make_client()
        self.bucket = self.client.bucket(self.bucket_name)
        self._stats = {"uploaded_files": 0, "uploaded_bytes": 0}

    def _make_client(self):
        key = settings.gcp_service_account_key
        if not key:
            raise RuntimeError(
                "GCP_SERVICE_ACCOUNT_KEY is required for GCSAssetStorage"
            )

        # If key looks like a path, use from_service_account_file
        try:
            if key.strip().startswith("{"):
                info = json.loads(key)
                creds = service_account.Credentials.from_service_account_info(info)
                return storage.Client(
                    project=settings.asset_gcp_project, credentials=creds
                )
        except Exception:
            pass

        # fallback: treat as path
        return storage.Client.from_service_account_json(
            key, project=settings.asset_gcp_project
        )

    def _validate_path_component(self, component: str) -> None:
        """Validate path component to prevent path traversal attacks."""
        if not component:
            raise ValueError("Path component cannot be empty")

        # Disallow path traversal sequences
        forbidden = ["..", ".", "/", "\\", "\x00"]
        for forbidden_str in forbidden:
            if forbidden_str in component:
                raise ValueError(f"Invalid path component: contains '{forbidden_str}'")

        # Ensure it's alphanumeric with limited special chars
        if not all(c.isalnum() or c in "-_" for c in component):
            raise ValueError(
                "Path component must be alphanumeric with hyphens/underscores only"
            )

    def _blob_name(self, lead_id: str) -> str:
        """Generate blob name with path traversal protection."""
        self._validate_path_component(lead_id)
        return f"assets/{lead_id}/{uuid.uuid4().hex}"

    def _gcloud_retry(self):
        return gcloud_retry.Retry(
            initial=0.1, maximum=10.0, multiplier=2.0, deadline=60.0
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential_jitter(initial=0.1, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def upload_stream(
        self, stream: BinaryIO, lead_id: str, checksum: str, content_type: str
    ) -> Tuple[str, int]:
        name = self._blob_name(lead_id)
        blob = self.bucket.blob(name)
        # configure chunk size for resumable uploads
        blob.chunk_size = settings.asset_upload_chunk_size
        blob.content_type = content_type
        blob.metadata = {"checksum": checksum, "leadId": lead_id, "pinned": "false"}

        # Use upload_from_file which supports resumable uploads when chunk_size set
        stream.seek(0)
        blob.upload_from_file(
            stream,
            content_type=content_type,
            timeout=settings.asset_download_timeout,
            retry=self._gcloud_retry(),  # pyright: ignore[reportArgumentType]
        )

        # update stats
        try:
            size = blob.size or 0
        except Exception:
            size = 0
        self._stats["uploaded_files"] += 1
        self._stats["uploaded_bytes"] += int(size)

        uri = f"gs://{self.bucket_name}/{name}"
        return uri, int(size)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.1, max=5),
        retry=retry_if_exception_type(Exception),
    )
    def delete(self, uri: str) -> None:
        if not uri.startswith("gs://"):
            raise ValueError("invalid gcs uri")
        # parse name
        parts = uri[len("gs://") :].split("/", 1)
        if len(parts) != 2:
            raise ValueError("invalid gcs uri")
        bucket, name = parts
        if bucket != self.bucket_name:
            # only operate on configured bucket
            raise ValueError("attempt to delete object outside configured bucket")
        blob = self.bucket.blob(name)
        blob.delete(retry=self._gcloud_retry())  # type: ignore[arg-type]

    def generate_signed_url(self, uri: str, expires_seconds: int) -> str:
        if not uri.startswith("gs://"):
            raise ValueError("invalid gcs uri")
        parts = uri[len("gs://") :].split("/", 1)
        bucket, name = parts
        if bucket != self.bucket_name:
            raise ValueError("uri bucket mismatch")
        blob = self.bucket.blob(name)
        # v4 signed URL
        url = blob.generate_signed_url(
            expiration=timedelta(seconds=expires_seconds), version="v4"
        )
        return url

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
