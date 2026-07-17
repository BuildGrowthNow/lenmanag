#!/usr/bin/env python3
"""Verify test user exists and password works."""

import asyncio
from app.core.users import UserRepository


async def verify_test_user():
    """Verify test user for API testing."""
    repo = UserRepository()

    email = "ai-agent@lenquant.internal"
    password = "LQ$aiAgent2026!Secure#TestOnly"

    # Check if user exists
    user = await repo.get_user_by_email(email)
    if not user:
        print(f"[ERROR] User {email} not found in database")
        return False

    print(f"[OK] User found: {email}")
    print(f"  ID: {user['_id']}")
    print(f"  Verified: {user.get('is_verified', False)}")
    print(f"  Created: {user.get('created_at')}")

    # Verify password
    verified_user = await repo.verify_password(email, password)
    if verified_user:
        print("[OK] Password verification successful")
        return True
    else:
        print("[ERROR] Password verification failed")
        return False


if __name__ == "__main__":
    asyncio.run(verify_test_user())
