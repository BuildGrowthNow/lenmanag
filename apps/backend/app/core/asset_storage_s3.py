from __future__ import annotations

import logging
import secrets
from typing import BinaryIO, Dict, Tuple

import boto3
from botocore.config import Config as BotoConfig

from .asset_storage import AssetStorage
from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class S3AssetStorage(AssetStorage):
    """AWS S3 asset storage backend."""

    def __init__(self):
        boto_config = BotoConfig(
            region_name=settings.asset_s3_region,
            retries={"max_attempts": 3, "mode": "adaptive"},
        )
        self.client = boto3.client("s3", config=boto_config)
        self.bucket = settings.asset_s3_bucket
        self.prefix = settings.asset_s3_prefix
        self._stats: Dict[str, int] = {"stored_files": 0, "stored_bytes": 0}

        if not self.bucket:
            raise RuntimeError(
                "ASSET_S3_BUCKET is required when ASSET_STORAGE_BACKEND=s3"
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

    def _key(self, lead_id: str, suffix: str) -> str:
        """Generate S3 key with path traversal protection."""
        self._validate_path_component(lead_id)
        self._validate_path_component(suffix)
        return f"{self.prefix}{lead_id}/{suffix}"

    def upload_stream(
        self, stream: BinaryIO, lead_id: str, checksum: str, content_type: str
    ) -> Tuple[str, int]:
        suffix = f"{secrets.token_hex(12)}"
        key = self._key(lead_id, suffix)

        data = stream.read()
        bytes_written = len(data)

        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ChecksumSHA256=checksum if len(checksum) == 44 else None,
        )

        self._stats["stored_files"] += 1
        self._stats["stored_bytes"] += bytes_written

        uri = f"s3://{self.bucket}/{key}"
        return uri, bytes_written

    def delete(self, uri: str) -> None:
        if not uri.startswith("s3://"):
            raise ValueError("invalid S3 uri")
        path = uri[len("s3://") :]
        bucket, key = path.split("/", 1)
        self.client.delete_object(Bucket=bucket, Key=key)

    def generate_signed_url(self, uri: str, expires_seconds: int) -> str:
        if not uri.startswith("s3://"):
            raise ValueError("invalid S3 uri")
        path = uri[len("s3://") :]
        bucket, key = path.split("/", 1)
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
        return url

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
