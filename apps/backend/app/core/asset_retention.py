from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

from app.core.mongo import get_database

from .asset_metadata import ASSET_COLLECTION
from .asset_storage import LocalAssetStorage
from .config import get_settings

try:
    from .asset_storage_gcs import GCSAssetStorage
except Exception:
    GCSAssetStorage = None
try:
    from .asset_storage_s3 import S3AssetStorage
except Exception:
    S3AssetStorage = None
from prometheus_client import Counter

# Metrics
PURGE_COUNTER = Counter("asset_purge_count", "Number of purged assets")
PURGE_BYTES = Counter("asset_purge_bytes", "Bytes purged by retention job")


@dataclass
class PurgeResult:
    purged_count: int = 0
    purged_bytes: int = 0
    errors: int = 0


@dataclass
class StorageStats:
    total_bytes: int = 0
    file_count: int = 0
    by_type: Dict[str, int] = None


class AssetRetentionManager:
    def __init__(self):
        self.settings = get_settings()

    def _local_purge(self) -> PurgeResult:
        base = Path(self.settings.asset_local_path)
        result = PurgeResult()
        if not base.exists():
            return result
        ttl = datetime.now(timezone.utc) - timedelta(
            days=self.settings.asset_retention_days
        )
        for f in base.rglob("*"):
            if not f.is_file():
                continue
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime < ttl:
                    size = f.stat().st_size
                    f.unlink()
                    result.purged_count += 1
                    result.purged_bytes += size
                    PURGE_COUNTER.inc()
                    PURGE_BYTES.inc(size)
            except Exception:
                result.errors += 1
        return result

    def purge_expired_assets(self) -> PurgeResult:
        result = self._local_purge()
        db = get_database()
        col = db[ASSET_COLLECTION]

        # find expired and not pinned
        now = datetime.utcnow()
        cursor = col.find({"expiresAt": {"$lte": now}, "pinned": {"$ne": True}})
        local_store = LocalAssetStorage(self.settings.asset_local_path)
        gcs_store = None
        s3_store = None
        if self.settings.asset_storage_backend == "s3" and S3AssetStorage is not None:
            try:
                s3_store = S3AssetStorage()
            except Exception:
                s3_store = None
        elif self.settings.asset_storage_backend == "gcp" and GCSAssetStorage is not None:
            try:
                gcs_store = GCSAssetStorage()
            except Exception:
                gcs_store = None

        async def _iter_and_purge():
            documents = await cursor.to_list(length=None)
            for doc in documents:
                uri = doc.get("cachedUri")
                try:
                    if not uri:
                        await col.delete_one({"_id": doc["_id"]})
                        continue
                    size = int(doc.get("bytes") or 0)
                    if uri.startswith("local://"):
                        local_store.delete(uri)
                    elif uri.startswith("s3://") and s3_store:
                        s3_store.delete(uri)
                    elif uri.startswith("gs://") and gcs_store:
                        gcs_store.delete(uri)

                    await col.delete_one({"_id": doc["_id"]})
                    result.purged_count += 1
                    result.purged_bytes += size
                    PURGE_COUNTER.inc()
                    PURGE_BYTES.inc(size)
                except Exception:
                    result.errors += 1

        import asyncio

        asyncio.run(_iter_and_purge())

        return result

    def get_storage_stats(self) -> StorageStats:
        base = Path(self.settings.asset_local_path)
        stats = StorageStats(by_type={})
        if not base.exists():
            return stats
        total = 0
        count = 0
        for f in base.iterdir():
            try:
                size = f.stat().st_size
                total += size
                count += 1
                # attempt to infer type by filename or parent dir
                ext = f.suffix.lstrip(".").lower() or "bin"
                stats.by_type[ext] = stats.by_type.get(ext, 0) + 1
            except Exception:
                continue
        stats.total_bytes = total
        stats.file_count = count
        return stats

    def pin_assets(self, lead_id: str) -> None:
        # placeholder: mark assets as pinned (extend TTL) in a real metadata store
        return None

    def unpin_assets(self, lead_id: str) -> None:
        return None
