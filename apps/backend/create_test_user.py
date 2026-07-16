#!/usr/bin/env python3
"""Create a test user for API testing."""

import asyncio
from app.core.users import UserRepository


async def create_test_user():
    """Create test user for API testing."""
    repo = UserRepository()
    await repo.ensure_indexes()

    email = "test@lenmanag.local"
    password = "TestPassword123!"

    # Check if user already exists
    existing = await repo.get_user_by_email(email)
    if existing:
        print(f"User {email} already exists (ID: {existing['_id']})")
        return existing

    # Create new user
    user = await repo.create_user(email=email, password=password)
    print(f"✓ Created test user: {email}")
    print(f"  ID: {user['_id']}")
    print(f"  Password: {password}")

    # Also verify the user immediately for testing convenience
    if user.get("verification_token"):
        verified = await repo.verify_email(user["verification_token"])
        if verified:
            print("✓ Verified user email")

    return user


if __name__ == "__main__":
    asyncio.run(create_test_user())
