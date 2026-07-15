import os
import io
import uuid
import pytest

GCP_KEY = os.environ.get('GCP_SERVICE_ACCOUNT_KEY')
BUCKET = os.environ.get('ASSET_GCP_BUCKET')

pytestmark = pytest.mark.skipif(not GCP_KEY or not BUCKET, reason="GCP credentials not provided")


def test_gcs_upload_and_signed_url():
    from app.core.asset_storage_gcs import GCSAssetStorage
    store = GCSAssetStorage()
    data = b"integration-test-data-" + uuid.uuid4().bytes
    stream = io.BytesIO(data)
    uri, size = store.upload_stream(stream, "testlead", "checksum", "application/octet-stream")
    assert uri.startswith('gs://')
    url = store.generate_signed_url(uri, expires_seconds=60)
    assert url.startswith('http')
    # cleanup
    store.delete(uri)

