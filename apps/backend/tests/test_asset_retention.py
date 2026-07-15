import os
import tempfile
from pathlib import Path
from app.core.asset_retention import AssetRetentionManager
from app.core.config import get_settings


def test_purge_local_assets(tmp_path):
    settings = get_settings()
    orig_path = settings.asset_local_path
    orig_days = settings.asset_retention_days
    settings.asset_local_path = str(tmp_path)
    settings.asset_retention_days = 0

    # create two files: one old, one new
    old = Path(tempfile.mkdtemp(dir=tmp_path)) / "old.bin"
    old.write_bytes(b"x" * 10)
    new = Path(tmp_path) / "new.bin"
    new.write_bytes(b"y" * 20)

    # set mtime of old to far past
    import time

    os.utime(old, (time.time() - 3600 * 24 * 10, time.time() - 3600 * 24 * 10))

    mgr = AssetRetentionManager()
    result = mgr.purge_expired_assets()
    assert result.purged_count >= 1

    # cleanup restore
    settings.asset_local_path = orig_path
    settings.asset_retention_days = orig_days
