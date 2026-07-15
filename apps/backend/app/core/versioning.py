from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from fastapi import Header, HTTPException, Request

from app.schemas.response import ResponseMeta

SUPPORTED_API_VERSIONS: tuple[str, ...] = ("1",)
DEFAULT_API_VERSION = "1"
VENDOR_MEDIA_TYPE_PREFIX = "application/vnd.lenmanag"
VERSION_HEADER_NAME = "X-API-Version"


def _normalize_version(raw: str | None) -> str:
    if not raw:
        return DEFAULT_API_VERSION
    cleaned = raw.strip().lower()
    if cleaned.startswith("v"):
        cleaned = cleaned[1:]
    if cleaned not in SUPPORTED_API_VERSIONS:
        raise HTTPException(status_code=406, detail=f"Unsupported API version '{raw}'.")
    return cleaned


def _extract_accept_version(accept_header: str | None) -> str | None:
    if not accept_header:
        return None
    for media_range in accept_header.split(","):
        media_type = media_range.strip()
        if not media_type.startswith(VENDOR_MEDIA_TYPE_PREFIX):
            continue
        suffix = media_type[len(VENDOR_MEDIA_TYPE_PREFIX) :].lstrip(".")
        version_token = suffix.split("+", 1)[0]
        if version_token:
            return version_token
    return None


def negotiate_api_version(explicit_version: str | None, accept_header: str | None) -> str:
    token = explicit_version or _extract_accept_version(accept_header)
    return _normalize_version(token)


def enforce_api_version(expected_version: str) -> Callable:
    normalized_expected = _normalize_version(expected_version)

    async def dependency(
        request: Request,
        x_api_version: str | None = Header(default=None, alias=VERSION_HEADER_NAME),
        accept: str | None = Header(default=None),
    ) -> str:
        negotiated = negotiate_api_version(x_api_version, accept)
        if negotiated != normalized_expected:
            raise HTTPException(
                status_code=406,
                detail=f"Requested API version 'v{negotiated}' does not match 'v{normalized_expected}'.",
            )
        request.state.api_version = f"v{negotiated}"
        return request.state.api_version

    return dependency


def ensure_request_id(request: Request) -> str:
    if getattr(request.state, "request_id", None):
        return request.state.request_id
    request.state.request_id = uuid4().hex
    return request.state.request_id


def current_api_version(request: Request) -> str:
    return getattr(request.state, "api_version", f"v{DEFAULT_API_VERSION}")


def response_meta(request: Request) -> ResponseMeta:
    return ResponseMeta(
        version=current_api_version(request),
        requestId=ensure_request_id(request),
        generatedAt=datetime.now(timezone.utc),
    )
