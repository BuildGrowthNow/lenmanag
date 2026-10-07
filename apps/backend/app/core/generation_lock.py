"""Global Redis capacity for active website variants."""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

import redis.asyncio as redis
from app.core.config import get_settings

GENERATION_LOCK_KEY = "lenquant:generation:active"
LOCK_TIMEOUT_SECONDS = (
    120  # Renewed while alive; crashes free capacity within two minutes.
)


class GenerationLockTimeout(Exception):
    pass


_ADMIT = """
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[3]), ARGV[1])
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[3]) + 120)
return 1
"""


@asynccontextmanager
async def generation_lock(
    timeout_seconds: int | None = None,
    *,
    key: str = GENERATION_LOCK_KEY,
    limit: int | None = None,
):
    settings = get_settings()
    capacity = max(
        1, limit if limit is not None else settings.generation_max_concurrent
    )
    client = redis.from_url(settings.celery_broker_url, decode_responses=True)
    lease_id = uuid4().hex
    start = time.monotonic()
    acquired = False
    heartbeat = None
    try:
        while not await client.eval(
            _ADMIT, 1, key, lease_id, capacity, LOCK_TIMEOUT_SECONDS
        ):
            if (
                timeout_seconds is not None
                and time.monotonic() - start >= timeout_seconds
            ):
                raise GenerationLockTimeout("Timed out waiting for generation capacity")
            await asyncio.sleep(1)
        acquired = True

        async def renew():
            while True:
                await asyncio.sleep(30)
                await client.eval(
                    "local t=tonumber(redis.call('TIME')[1]); return redis.call('ZADD', KEYS[1], 'XX', t+tonumber(ARGV[2]), ARGV[1])",
                    1,
                    key,
                    lease_id,
                    LOCK_TIMEOUT_SECONDS,
                )

        heartbeat = asyncio.create_task(renew())
        yield
    finally:
        if heartbeat:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await heartbeat
        try:
            if acquired:
                await client.zrem(key, lease_id)
        finally:
            await client.aclose()
