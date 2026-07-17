#!/usr/bin/env python3
"""List all users in the database."""

import asyncio
from app.core.users import UserRepository


async def list_users():
    """List all users."""
    repo = UserRepository()
    users = await repo.collection.find({}).to_list(length=100)

    if not users:
        print("[INFO] No users found in database")
        return

    print(f"[INFO] Found {len(users)} users:")
    for user in users:
        print(
            f"  - {user['email']} (ID: {user['_id']}, Verified: {user.get('is_verified', False)})"
        )


if __name__ == "__main__":
    asyncio.run(list_users())
