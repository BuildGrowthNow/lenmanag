"""
Distributed lock for ensuring sequential site generation across all workers.

Uses Redis to enforce global sequential execution, preventing rate limits.
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global lock key in Redis
GENERATION_LOCK_KEY = "lenquant:generation:lock"
LOCK_TIMEOUT_SECONDS = 3600  # 1 hour max per generation


class GenerationLockTimeout(Exception):
    """Raised when unable to acquire generation lock within timeout."""

    pass


@asynccontextmanager
async def generation_lock(
    timeout_seconds: int = 300,
) -> AsyncGenerator[None, None]:
    """
    Distributed lock for site generation.

    Ensures only ONE generation task runs globally at any time,
    even across multiple workers/processes.

    Args:
        timeout_seconds: How long to wait for lock acquisition

    Raises:
        GenerationLockTimeout: If lock not acquired within timeout

    Usage:
        async with generation_lock(timeout_seconds=300):
            # Only one task can be here at a time globally
            await generate_site(...)
    """
    settings = get_settings()

    # Parse Redis URL from Celery broker
    redis_url = settings.celery_broker_url

    redis_client = redis.from_url(redis_url, decode_responses=True)

    lock_acquired = False
    lock_id = f"{time.time()}-{id(redis_client)}"  # Unique lock ID

    try:
        # Try to acquire lock
        start_time = time.monotonic()
        while True:
            # SET with NX (only if not exists) and EX (expiry)
            acquired = await redis_client.set(
                GENERATION_LOCK_KEY,
                lock_id,
                nx=True,
                ex=LOCK_TIMEOUT_SECONDS,
            )

            if acquired:
                lock_acquired = True
                elapsed = time.monotonic() - start_time
                if elapsed < 1:
                    logger.info("Generation lock acquired immediately")
                else:
                    logger.info(f"Generation lock acquired after {elapsed:.1f}s")
                break

            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed > timeout_seconds:
                logger.error(
                    f"Generation lock timeout after {timeout_seconds}s - "
                    "another generation may be stuck"
                )
                raise GenerationLockTimeout(
                    f"Could not acquire generation lock after {timeout_seconds}s"
                )

            # Log wait progress (warn if waiting too long)
            if elapsed > 60:
                logger.warning(
                    f"Long wait for generation lock: {elapsed:.0f}s elapsed "
                    f"(timeout at {timeout_seconds}s)"
                )
            else:
                logger.info(f"Waiting for generation lock... ({elapsed:.0f}s elapsed)")
            await asyncio.sleep(5)

        # Lock acquired, yield control
        yield

    finally:
        # Release lock if we acquired it
        if lock_acquired:
            # Atomic check-and-delete: only delete if we still own the lock
            current_value = await redis_client.get(GENERATION_LOCK_KEY)
            if current_value == lock_id:
                await redis_client.delete(GENERATION_LOCK_KEY)
            logger.info("Generation lock released")

        await redis_client.aclose()
