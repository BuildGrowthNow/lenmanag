from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import ReturnDocument

from app.core.mongo import get_database


ASSET_COLLECTION = "asset_metadata"
CrawlBudget_COLLECTION = "crawl_budget"


async def create_indexes() -> None:
    db = get_database()
    col = db[ASSET_COLLECTION]
    # TTL index on expiresAt
    await col.create_index("expiresAt", expireAfterSeconds=0)
    # index on leadId
    await col.create_index("leadId")


async def create_asset_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    db = get_database()
    col = db[ASSET_COLLECTION]
    await col.insert_one(doc)
    return doc


async def update_asset_doc(
    filter: Dict[str, Any], update: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    db = get_database()
    col = db[ASSET_COLLECTION]
    res = await col.find_one_and_update(
        filter, {"$set": update}, return_document=ReturnDocument.AFTER
    )
    return res


async def get_asset_by_id(_id: Any) -> Optional[Dict[str, Any]]:
    db = get_database()
    col = db[ASSET_COLLECTION]
    return await col.find_one({"_id": _id})


async def reserve_crawl_budget(
    crawl_id: str, inc_bytes: int, max_bytes: int
) -> Dict[str, Any]:
    """Atomically increment used_bytes for a crawl and ensure it does not exceed max_bytes.

    This uses an optimistic upsert: it increments and then checks; if over-limit it rolls back.
    Returns the updated crawl document on success.
    Raises ValueError if budget exceeded.
    """
    db = get_database()
    col = db[CrawlBudget_COLLECTION]
    now = datetime.utcnow()
    # upsert and increment
    doc = await col.find_one_and_update(
        {"_id": crawl_id},
        {
            "$inc": {"used_bytes": inc_bytes},
            "$setOnInsert": {"limit": max_bytes, "createdAt": now},
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    if doc is None:
        raise RuntimeError("failed to reserve crawl budget")

    used = int(doc.get("used_bytes", 0))
    if used > max_bytes:
        # rollback
        await col.update_one({"_id": crawl_id}, {"$inc": {"used_bytes": -inc_bytes}})
        raise ValueError("crawl budget exceeded")

    return doc
