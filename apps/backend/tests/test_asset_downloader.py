import os
from app.core.asset_downloader import AssetDownloader
from app.core.config import get_settings


def test_validate_mime_types():
    d = AssetDownloader()
    assert d.validate_mime_type("image/png")
    assert d.validate_mime_type("font/woff2")
    assert d.validate_mime_type("text/css")
    assert not d.validate_mime_type("application/json")


def test_download_disabled():
    settings = get_settings()
    orig = settings.asset_download_enabled
    settings.asset_download_enabled = False
    d = AssetDownloader()
    res = None
    # calling download_asset should quickly return with error when disabled
    import asyncio

    res = asyncio.run(d.download_asset("https://example.com/image.png", "testlead"))
    assert res.success is False
    assert res.error == "asset download disabled"
    settings.asset_download_enabled = orig
