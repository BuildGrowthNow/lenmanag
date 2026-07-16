from __future__ import annotations

import hmac
import hashlib
import os
import secrets
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO, Dict, Tuple

from .config import get_settings

settings = get_settings()


class AssetStorage(ABC):
    @abstractmethod
    def upload_stream(
        self, stream: BinaryIO, lead_id: str, checksum: str, content_type: str
    ) -> Tuple[str, int]:
        pass

    @abstractmethod
    def delete(self, uri: str) -> None:
        pass

    @abstractmethod
    def generate_signed_url(self, uri: str, expires_seconds: int) -> str:
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        pass


class LocalAssetStorage(AssetStorage):
    """Simple local filesystem asset store with atomic writes and HMAC-signed local URLs.

    URIs returned have the form: local://{relpath}
    Signed URLs point to an internal route and include an HMAC signature that must
    be validated by the serving endpoint.
    """

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or settings.asset_local_path)
        os.makedirs(self.base_path, exist_ok=True)
        self._stats = {"stored_files": 0, "stored_bytes": 0}

    def _safe_relpath(self, filename: str) -> str:
        # Ensure no path traversal: only allow name and simple chars
        name = Path(filename).name
        if name in ("", ".", ".."):
            raise ValueError("invalid filename")
        return name

    def upload_stream(
        self, stream: BinaryIO, lead_id: str, checksum: str, content_type: str
    ) -> Tuple[str, int]:
        # create deterministic filename using secure random and lead id
        relname = f"{lead_id}-{secrets.token_hex(12)}"
        relname = self._safe_relpath(relname)
        dest = self.base_path / relname
        temp = self.base_path / (relname + ".tmp")
        bytes_written = 0
        with open(temp, "wb") as fh:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                fh.write(chunk)
                bytes_written += len(chunk)

        # atomic rename
        try:
            os.replace(temp, dest)
        except OSError:
            raise

        self._stats["stored_files"] += 1
        self._stats["stored_bytes"] += bytes_written

        uri = f"local://{relname}"
        return uri, bytes_written

    def delete(self, uri: str) -> None:
        if not uri.startswith("local://"):
            raise ValueError("invalid local uri")
        rel = uri[len("local://") :]
        rel = Path(self._safe_relpath(rel))
        path = self.base_path / rel
        try:
            path.unlink()
        except FileNotFoundError:
            return

    def generate_signed_url(self, uri: str, expires_seconds: int) -> str:
        # Create a signed token for the local asset URI. The serving endpoint
        # must validate the token using the same secret.
        if not uri.startswith("local://"):
            raise ValueError("invalid local uri")
        rel = uri[len("local://") :]
        exp = int(__import__("time").time()) + int(expires_seconds)
        payload = f"{rel}:{exp}".encode("utf-8")
        key = settings.session_secret.encode("utf-8")
        sig = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return f"/api/internal/assets/local/{rel}?exp={exp}&sig={sig}"

    def get_stats(self) -> Dict[str, int]:
        return dict(self._stats)
