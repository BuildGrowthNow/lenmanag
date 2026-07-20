#!/usr/bin/env python3
"""Create ops-agent test user for API testing."""

import asyncio
from app.core.users import UserRepository


async def create_ops_user():
    """Create ops-agent user for API/integration testing."""
    repo = UserRepository()
    await repo.ensure_indexes()

    email = "ops-agent@lenquant.internal"
    password = "LQ$opsAgent2026!Internal#Only"

    existing = await repo.get_user_by_email(email)
    if existing:
        print(f"User {email} already exists (ID: {existing['_id']})")
        return existing

    user = await repo.create_user(email=email, password=password)
    print(f"[OK] Created user: {email}")
    print(f"  ID: {user['_id']}")

    if user.get("verification_token"):
        verified = await repo.verify_email(user["verification_token"])
        if verified:
            print("[OK] Verified email")

    return user


if __name__ == "__main__":
    asyncio.run(create_ops_user())
