"""
Migration: backfill userId on generated_sites and user_id on message_drafts.

For each generated_site, look up the linked lead's user_id and copy it.
For each message_draft, look up the linked lead's user_id and copy it.
Documents whose lead is missing or has no user_id are assigned FALLBACK_USER_ID.
"""

from __future__ import annotations

import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient

FALLBACK_USER_ID = os.getenv("FALLBACK_USER_ID", "6a59e2aca2a1aebf9b7dd127")


async def main() -> None:
    uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGODB_DB_NAME", "lenmanag")
    if not uri:
        print("ERROR: MONGODB_URI env var is required", file=sys.stderr)
        sys.exit(1)

    client: AsyncIOMotorClient = AsyncIOMotorClient(uri)
    db = client[db_name]

    # ── generated_sites ────────────────────────────────────────────────────────
    print("Backfilling generated_sites.userId …")
    sites_updated = 0
    sites_fallback = 0
    cursor = db["generated_sites"].find(
        {"$or": [{"userId": {"$exists": False}}, {"userId": ""}]},
        {"id": 1, "leadId": 1},
    )
    async for site in cursor:
        lead_id = site.get("leadId")
        user_id = FALLBACK_USER_ID
        if lead_id:
            lead = await db["leads"].find_one({"id": lead_id}, {"user_id": 1})
            if lead and lead.get("user_id"):
                user_id = str(lead["user_id"])
            else:
                sites_fallback += 1
        else:
            sites_fallback += 1
        await db["generated_sites"].update_one(
            {"id": site["id"]},
            {"$set": {"userId": user_id}},
        )
        sites_updated += 1

    print(f"  updated {sites_updated} sites ({sites_fallback} used fallback)")

    # ── message_drafts ─────────────────────────────────────────────────────────
    print("Backfilling message_drafts.user_id …")
    drafts_updated = 0
    drafts_fallback = 0
    cursor = db["message_drafts"].find(
        {"$or": [{"user_id": {"$exists": False}}, {"user_id": ""}]},
        {"id": 1, "leadId": 1},
    )
    async for draft in cursor:
        lead_id = draft.get("leadId")
        user_id = FALLBACK_USER_ID
        if lead_id:
            lead = await db["leads"].find_one({"id": lead_id}, {"user_id": 1})
            if lead and lead.get("user_id"):
                user_id = str(lead["user_id"])
            else:
                drafts_fallback += 1
        else:
            drafts_fallback += 1
        await db["message_drafts"].update_one(
            {"id": draft["id"]},
            {"$set": {"user_id": user_id}},
        )
        drafts_updated += 1

    print(f"  updated {drafts_updated} drafts ({drafts_fallback} used fallback)")

    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
