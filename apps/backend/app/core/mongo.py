from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: Optional[AsyncIOMotorClient] = None


def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    global _client
    settings = get_settings()
    if not settings.mongodb_uri:
        return None
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_database() -> Optional[AsyncIOMotorDatabase]:
    client = get_mongo_client()
    if client is None:
        return None
    return client[get_settings().mongodb_db_name]
