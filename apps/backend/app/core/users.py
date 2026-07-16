from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.mongo import get_database


def _now() -> datetime:
    return datetime.now(timezone.utc)


class UserRepository:
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db or get_database()
        self.collection = self.db["users"]

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("email", unique=True)
        await self.collection.create_index("verification_token")

    async def create_user(
        self,
        email: str,
        password: str,
    ) -> dict:
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        verification_token = secrets.token_urlsafe(32)

        user_doc = {
            "email": email.lower(),
            "hashed_password": hashed_password,
            "is_verified": False,
            "verification_token": verification_token,
            "created_at": _now(),
            "updated_at": _now(),
        }

        result = await self.collection.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        return user_doc

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        return await self.collection.find_one({"email": email.lower()})

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        from bson import ObjectId
        try:
            return await self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

    async def verify_password(self, email: str, password: str) -> Optional[dict]:
        user = await self.get_user_by_email(email)
        if not user:
            return None

        if bcrypt.checkpw(password.encode("utf-8"), user["hashed_password"].encode("utf-8")):
            return user
        return None

    async def verify_email(self, token: str) -> Optional[dict]:
        user = await self.collection.find_one({"verification_token": token})
        if not user:
            return None

        await self.collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "is_verified": True,
                    "verification_token": None,
                    "updated_at": _now(),
                }
            }
        )

        user["is_verified"] = True
        user["verification_token"] = None
        return user

    async def update_verification_token(self, email: str) -> Optional[str]:
        verification_token = secrets.token_urlsafe(32)
        result = await self.collection.update_one(
            {"email": email.lower()},
            {
                "$set": {
                    "verification_token": verification_token,
                    "updated_at": _now(),
                }
            }
        )

        if result.modified_count > 0:
            return verification_token
        return None
