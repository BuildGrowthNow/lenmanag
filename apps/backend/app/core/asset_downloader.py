from __future__ import annotations

import asyncio
import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import httpx
import tempfile

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)

from .asset_storage import LocalAssetStorage

try:
    from .asset_storage_gcs import GCSAssetStorage
except Exception:  # pragma: no cover - optional dependency at import time
    GCSAssetStorage = None
try:
    from .asset_storage_s3 import S3AssetStorage
except Exception:  # pragma: no cover - optional dependency at import time
    S3AssetStorage = None
from prometheus_client import Counter, Histogram

# Metrics
from .config import get_settings
from .audit import write_asset_audit_log

DOWNLOAD_COUNTER = Counter("asset_download_total", "Total asset download attempts")
DOWNLOAD_FAILURES = Counter(
    "asset_download_failures_total", "Total failed asset downloads"
)
DOWNLOAD_BYTES = Counter("asset_download_bytes_total", "Total bytes downloaded")
DOWNLOAD_LATENCY = Histogram(
    "asset_download_latency_seconds", "Histogram of asset download latencies"
)


@dataclass
class AssetDownloadResult:
    source_url: str
    success: bool
    content_type: Optional[str] = None
    bytes: Optional[int] = None
    cached_uri: Optional[str] = None
    cached_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    checksum: Optional[str] = None
    error: Optional[str] = None


class AssetDownloader:
    def __init__(self):
        self.settings = get_settings()
        self._semaphore = asyncio.Semaphore(self.settings.asset_concurrent_downloads)
        # initialize storage backend
        backend = (self.settings.asset_storage_backend or "local").lower()
        if backend == "s3":
            if S3AssetStorage is None:
                raise RuntimeError("S3AssetStorage not available; missing dependency")
            self.storage = S3AssetStorage()
        elif backend == "gcp":
            if GCSAssetStorage is None:
                raise RuntimeError("GCSAssetStorage not available; missing dependency")
            self.storage = GCSAssetStorage()
        else:
            self.storage = LocalAssetStorage(self.settings.asset_local_path)

    def validate_mime_type(self, content_type: str) -> bool:
        if not content_type:
            return False
        ct = content_type.split(";")[0].strip().lower()
        if ct.startswith("image/"):
            return True
        if ct.startswith("font/"):
            return True
        if ct == "text/css":
            return True
        return False

    def enforce_byte_limit(self, content: bytes, max_bytes: int | None = None) -> bool:
        if max_bytes is None:
            max_bytes = self.settings.asset_max_file_bytes
        return len(content) <= max_bytes

    def enforce_aggregate_limit(
        self, total_bytes: int, max_bytes: int | None = None
    ) -> bool:
        if max_bytes is None:
            max_bytes = self.settings.asset_max_aggregate_bytes
        return total_bytes <= max_bytes

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_jitter(initial=0.1, max=5),
        retry=retry_if_exception_type(Exception),
    )
    async def _stream_to_tempfile(
        self, client: httpx.AsyncClient, url: str, temp_path: str, max_bytes: int
    ) -> int:
        bytes_written = 0
        hasher = hashlib.sha256()
        async with client.stream("GET", url) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                if not chunk:
                    break
                bytes_written += len(chunk)
                if max_bytes and bytes_written > max_bytes:
                    raise ValueError(f"file exceeded max bytes limit: {bytes_written}")
                # write to file in thread to avoid blocking
                await asyncio.to_thread(lambda b: open(temp_path, "ab").write(b), chunk)
                hasher.update(chunk)

        return bytes_written

    async def download_asset(
        self, url: str, lead_id: str, actor_user_id: Optional[str] = None
    ) -> AssetDownloadResult:
        res = AssetDownloadResult(source_url=url, success=False)
        if not self.settings.asset_download_enabled:
            res.error = "asset download disabled"
            return res

        timeout = httpx.Timeout(self.settings.asset_download_timeout)
        headers = {"User-Agent": "LenQuantAssetFetcher/1.0"}

        async with self._semaphore:
            temp_f = None
            try:
                DOWNLOAD_COUNTER.inc()
                start = __import__("time").time()
                async with httpx.AsyncClient(
                    timeout=timeout, headers=headers, follow_redirects=True
                ) as client:
                    async with client.stream("GET", url) as resp:
                        resp.raise_for_status()
                        res.content_type = resp.headers.get("content-type")
                        if not self.validate_mime_type(res.content_type or ""):
                            res.error = f"invalid content-type: {res.content_type}"
                            return res

                        # quick check content-length
                        cl = resp.headers.get("content-length")
                        if cl:
                            try:
                                if int(cl) > self.settings.asset_max_file_bytes:
                                    res.error = (
                                        f"file too large by content-length: {cl}"
                                    )
                                    return res
                            except Exception:
                                pass

                        # stream to tempfile
                        tf = tempfile.NamedTemporaryFile(delete=False)
                        temp_f = tf.name
                        tf.close()

                        # write streaming using helper
                        try:
                            await self._stream_to_tempfile(
                                client, url, temp_f, self.settings.asset_max_file_bytes
                            )
                        except Exception as ex:
                            # cleanup
                            try:
                                os.unlink(temp_f)
                            except Exception:
                                pass
                            res.error = str(ex)
                            return res

                        # compute checksum and open file for upload
                        hasher = hashlib.sha256()
                        with open(temp_f, "rb") as fh:
                            while True:
                                chunk = fh.read(64 * 1024)
                                if not chunk:
                                    break
                                hasher.update(chunk)
                        checksum = hasher.hexdigest()

                        # upload to storage
                        with open(temp_f, "rb") as fh:
                            uri, stored_bytes = self.storage.upload_stream(
                                fh,
                                lead_id,
                                checksum,
                                res.content_type or "application/octet-stream",
                            )

                        now = datetime.utcnow()
                        expires = now + timedelta(
                            days=self.settings.asset_retention_days
                        )

                        res.checksum = checksum
                        res.bytes = stored_bytes
                        res.cached_uri = uri
                        res.cached_at = now
                        res.expires_at = expires
                        res.success = True
                        DOWNLOAD_BYTES.inc(int(res.bytes or 0))
                        DOWNLOAD_LATENCY.observe(__import__("time").time() - start)

                        # Audit log successful download
                        await write_asset_audit_log(
                            actor_user_id=actor_user_id,
                            lead_id=lead_id,
                            asset_url=url,
                            action="asset_download",
                            metadata={
                                "bytes": stored_bytes,
                                "contentType": res.content_type,
                                "checksum": checksum,
                                "storageUri": uri,
                                "success": True,
                            },
                        )

                        return res
            except Exception as ex:
                DOWNLOAD_FAILURES.inc()
                res.error = str(ex)

                # Audit log failed download
                await write_asset_audit_log(
                    actor_user_id=actor_user_id,
                    lead_id=lead_id,
                    asset_url=url,
                    action="asset_download_failed",
                    metadata={
                        "error": str(ex),
                        "success": False,
                    },
                )

                return res
            finally:
                if temp_f:
                    try:
                        os.unlink(temp_f)
                    except Exception:
                        pass

    def _local_write(self, content: bytes, checksum: str) -> Path:
        base = Path(self.settings.asset_local_path)
        base.mkdir(parents=True, exist_ok=True)
        filename = f"{checksum}"
        path = base / filename
        with path.open("wb") as f:
            f.write(content)
        return path

    async def download_batch(
        self, urls: List[str], lead_id: str
    ) -> List[AssetDownloadResult]:
        results: List[AssetDownloadResult] = []
        total = 0

        async def _dl(u: str):
            nonlocal total
            r = await self.download_asset(u, lead_id)
            if r.bytes:
                total += r.bytes
            return r

        # limit concurrency handled by semaphore inside download_asset
        tasks = [asyncio.create_task(_dl(u)) for u in urls]
        for coro in asyncio.as_completed(tasks):
            r = await coro
            results.append(r)
            if r.bytes and not self.enforce_aggregate_limit(total):
                # stop remaining tasks
                for t in tasks:
                    if not t.done():
                        t.cancel()
                break

        return results
