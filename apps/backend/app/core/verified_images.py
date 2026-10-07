"""Source image catalogue: validate bytes once, then serve immutable local copies."""
from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import logging
import re
import socket
from io import BytesIO
from urllib.parse import urljoin, urlsplit

import boto3
import httpx
from bs4 import BeautifulSoup
from PIL import Image

from app.core.config import get_settings
from app.core.mongo import get_database

logger = logging.getLogger(__name__)


async def _public_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"https", "http"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Invalid source image URL")
    addresses = await asyncio.to_thread(socket.getaddrinfo, parts.hostname, parts.port or 443)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError("Source image must use a public address")


def image_candidates(extraction) -> list[dict]:
    candidates = []
    for image in extraction.extractedImages:
        if image.category not in {"client_logo", "testimonial", "decorative"}:
            candidates.append({"url": image.url, "description": image.altText or image.title or image.category})
    for page in extraction.pageInventory:
        for asset in page.assets:
            if asset.kind == "image":
                candidates.append({"url": asset.url, "description": asset.label or urlsplit(asset.url).path.rsplit("/", 1)[-1].replace("-", " ")})
        if not page.rawHtml:
            continue
        soup = BeautifulSoup(page.rawHtml, "html.parser")
        for node in soup.find_all("img"):
            value = node.get("data-src") or node.get("src")
            if value:
                candidates.append({"url": urljoin(page.url, value), "description": node.get("alt") or "Source website photograph"})
        for value in re.findall(r"url\(\s*['\"]?([^)'\"\s]+)", page.rawHtml):
            candidates.append({"url": urljoin(page.url, value), "description": "Source website background photograph"})
    seen = set()
    result = []
    for item in candidates:
        url = item["url"]
        if url in seen or re.search(r"favicon|logo|icon|badge|check.?mark|spacer|pixel|review.us.google|vid.splash.play|facebook.com/tr|bat.bing.com|ipromote.com", url, re.I):
            continue
        if urlsplit(url).scheme not in {"http", "https"}:
            continue
        seen.add(url)
        result.append(item)
        if len(result) >= 24:
            break
    return result


async def verified_image_catalog(extraction) -> list[dict]:
    candidates = image_candidates(extraction)
    database = get_database()
    semaphore = asyncio.Semaphore(3)
    settings = get_settings()

    async def cache(item, client):
        async with semaphore:
            digest = hashlib.sha256(item["url"].encode()).hexdigest()
            if database is not None:
                previous = await database.verified_images.find_one({"_id": digest})
                if previous:
                    return {"url": previous["url"], "description": item["description"], "sourceUrl": item["url"]}
            try:
                url = item["url"]
                for _ in range(5):
                    await _public_url(url)
                    async with client.stream("GET", url) as response:
                        if response.is_redirect:
                            url = urljoin(url, response.headers["location"])
                            continue
                        response.raise_for_status()
                        if not response.headers.get("content-type", "").startswith("image/"):
                            raise ValueError("Source returned non-image content")
                        content = bytearray()
                        async for chunk in response.aiter_bytes():
                            content.extend(chunk)
                            if len(content) > 8_000_000:
                                raise ValueError("Image exceeds size limit")
                        break
                else:
                    raise ValueError("Too many image redirects")
                def inspect():
                    with Image.open(BytesIO(content)) as image:
                        width, height = image.size
                        image_format = image.format
                        image.verify()
                        return width, height, image_format
                width, height, image_format = await asyncio.to_thread(inspect)
                if min(width, height) < 180 or width * height < 120_000:
                    raise ValueError("Image too small for a website photograph")
                mime = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif"}.get(image_format)
                if not mime or not settings.asset_s3_bucket:
                    raise ValueError("Image cannot be cached")
                suffix = mime.split("/")[1]
                key = f"{settings.asset_s3_prefix.strip('/')}/verified-images/{digest}.{suffix}"
                s3 = boto3.client("s3", region_name=settings.asset_s3_region)
                await asyncio.to_thread(s3.put_object, Bucket=settings.asset_s3_bucket, Key=key, Body=bytes(content), ContentType=mime, CacheControl="public, max-age=31536000, immutable")
                cached_url = f"https://{settings.asset_s3_bucket}.s3.amazonaws.com/{key}"
                if database is not None:
                    await database.verified_images.update_one({"_id": digest}, {"$set": {"url": cached_url, "sourceUrl": item["url"], "width": width, "height": height}}, upsert=True)
                return {"url": cached_url, "description": item["description"], "sourceUrl": item["url"]}
            except Exception as exc:
                logger.info("Omitting unavailable source photograph %s: %s", item["url"], type(exc).__name__)
                return None

    async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "Mozilla/5.0 LenQuantImageFetcher"}) as client:
        results = await asyncio.gather(*(cache(item, client) for item in candidates))
    return [item for item in results if item]


def enforce_image_catalog(html: str, css: str, catalog: list[dict]) -> tuple[str, str]:
    """Remove invented references rather than silently substituting unrelated photos."""
    allowed = {item["url"] for item in catalog}
    soup = BeautifulSoup(html, "html.parser")
    for image in list(soup.find_all(["img", "source"])):
        url = image.get("src")
        if url not in allowed:
            image.decompose()
            continue
        for attr in ("srcset", "data-src", "data-srcset", "onerror"):
            image.attrs.pop(attr, None)
    def css_url(match):
        url = match.group(2).strip()
        if url.startswith("data:image/") or url in allowed:
            return match.group(0)
        # Font URLs are not image references.
        if re.search(r"\.(?:woff2?|ttf|otf)(?:[?#]|$)", url, re.I):
            return match.group(0)
        return "none"
    css = re.sub(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css_url, css, flags=re.I)
    css = re.sub(r"cursor\s*:\s*none\b", "cursor: auto", css, flags=re.I)
    for node in list(soup.select(".custom-cursor, #custom-cursor, [data-custom-cursor]")):
        node.decompose()
    return str(soup), css
