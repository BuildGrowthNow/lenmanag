from __future__ import annotations

from typing import Optional

from .config import get_settings
from .asset_storage import LocalAssetStorage

try:
    from .asset_storage_gcs import GCSAssetStorage
except Exception:
    GCSAssetStorage = None
try:
    from .asset_storage_s3 import S3AssetStorage
except Exception:
    S3AssetStorage = None

settings = get_settings()


def get_asset_signed_url(uri: str, expiry: Optional[int] = None) -> str:
    expiry = expiry or settings.asset_gcp_signed_url_expiry
    backend = (settings.asset_storage_backend or "local").lower()
    if backend == "s3":
        if S3AssetStorage is None:
            raise RuntimeError("S3AssetStorage not available")
        store = S3AssetStorage()
        return store.generate_signed_url(uri, expiry)
    if backend == "gcp":
        if GCSAssetStorage is None:
            raise RuntimeError("GCSAssetStorage not available")
        store = GCSAssetStorage()
        return store.generate_signed_url(uri, expiry)
    store = LocalAssetStorage(settings.asset_local_path)
    return store.generate_signed_url(uri, expiry)
