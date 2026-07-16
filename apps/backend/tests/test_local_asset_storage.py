import io
from app.core.asset_storage import LocalAssetStorage


def test_local_upload_and_delete(tmp_path, monkeypatch):
    base = tmp_path / "assets"
    store = LocalAssetStorage(str(base))
    data = b"hello world"
    stream = io.BytesIO(data)
    uri, size = store.upload_stream(stream, "lead123", "deadbeef", "image/png")
    assert size == len(data)
    assert uri.startswith("local://")
    # ensure file exists
    rel = uri[len("local://") :]
    path = base / rel
    assert path.exists()
    # delete
    store.delete(uri)
    assert not path.exists()
