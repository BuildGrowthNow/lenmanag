from __future__ import annotations

from typing import Any, Optional, Sequence

import mongomock
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: Optional[AsyncIOMotorClient | "_AsyncMongoMockClient"] = None


class _AsyncMongoMockCursor:
    def __init__(self, documents: Sequence[dict[str, Any]]):
        self._documents = list(documents)
        self._sort_fields: list[tuple[str, int]] = []
        self._skip: int = 0
        self._limit: Optional[int] = None

    def sort(self, key_or_list: Any, direction: Optional[int] = None) -> "_AsyncMongoMockCursor":
        if isinstance(key_or_list, list):
            self._sort_fields.extend([(item[0], item[1]) for item in key_or_list])
        else:
            self._sort_fields.append((key_or_list, direction or 1))
        return self

    def skip(self, count: int) -> "_AsyncMongoMockCursor":
        self._skip = count
        return self

    def limit(self, count: int) -> "_AsyncMongoMockCursor":
        self._limit = count
        return self

    async def to_list(self, length: Optional[int] = None) -> list[dict[str, Any]]:
        docs = list(self._documents)
        for key, direction in reversed(self._sort_fields):
            docs.sort(key=lambda item, field=key: item.get(field), reverse=direction == -1)
        if self._skip:
            docs = docs[self._skip :]
        cap = self._limit if self._limit is not None else length
        if cap is not None:
            docs = docs[:cap]
        return docs


class _AsyncMongoMockCollection:
    def __init__(self, collection: mongomock.collection.Collection):
        self._collection = collection

    async def insert_one(self, document: dict[str, Any]):
        return self._collection.insert_one(document)

    async def insert_many(self, documents: Sequence[dict[str, Any]]):
        return self._collection.insert_many(list(documents))

    async def replace_one(self, *args, **kwargs):
        return self._collection.replace_one(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        return self._collection.update_one(*args, **kwargs)

    async def delete_many(self, *args, **kwargs):
        return self._collection.delete_many(*args, **kwargs)

    async def find_one(self, *args, **kwargs) -> dict[str, Any] | None:
        doc = self._collection.find_one(*args, **kwargs)
        return dict(doc) if doc else None

    def find(self, *args, **kwargs) -> _AsyncMongoMockCursor:
        docs = list(self._collection.find(*args, **kwargs))
        return _AsyncMongoMockCursor(docs)

    async def count_documents(self, *args, **kwargs) -> int:
        return self._collection.count_documents(*args, **kwargs)

    async def create_index(self, *args, **kwargs):
        return self._collection.create_index(*args, **kwargs)


class _AsyncMongoMockDatabase:
    def __init__(self, database: mongomock.database.Database):
        self._database = database

    def __getitem__(self, name: str) -> _AsyncMongoMockCollection:
        return _AsyncMongoMockCollection(self._database[name])


class _AsyncMongoMockClient:
    def __init__(self):
        self._client = mongomock.MongoClient()
        self._admin = _AsyncMongoMockAdmin()

    def __getitem__(self, name: str) -> _AsyncMongoMockDatabase:
        return _AsyncMongoMockDatabase(self._client[name])

    @property
    def admin(self) -> "_AsyncMongoMockAdmin":
        return self._admin

    def close(self) -> None:
        self._client.close()


class _AsyncMongoMockAdmin:
    async def command(self, *_args, **_kwargs) -> dict[str, Any]:
        return {"ok": 1}


def _build_client() -> AsyncIOMotorClient | _AsyncMongoMockClient:
    settings = get_settings()
    if settings.mongodb_uri:
        # Configure connection pool to prevent connection exhaustion
        return AsyncIOMotorClient(
            settings.mongodb_uri,
            maxPoolSize=50,  # Maximum number of connections in pool
            minPoolSize=10,  # Minimum number of connections maintained
            maxIdleTimeMS=45000,  # Close idle connections after 45s
            waitQueueTimeoutMS=10000,  # Wait up to 10s for connection from pool
            serverSelectionTimeoutMS=5000,  # Timeout for server selection
            connectTimeoutMS=10000,  # Timeout for socket connection
            socketTimeoutMS=45000,  # Timeout for socket operations
        )
    return _AsyncMongoMockClient()


def get_mongo_client() -> AsyncIOMotorClient | _AsyncMongoMockClient:
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def get_database() -> AsyncIOMotorDatabase | _AsyncMongoMockDatabase:
    client = get_mongo_client()
    return client[get_settings().mongodb_db_name]
