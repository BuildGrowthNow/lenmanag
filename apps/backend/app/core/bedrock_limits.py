"""Shared Redis admission limits for every Bedrock request, across workers/APIs."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager, suppress
from uuid import uuid4

import redis.asyncio as redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Redis's clock and Lua make admission atomic across all processes. Inflight
# reservations remain charged until completion; usage stays charged for 60s
# afterwards, including Claude's output-token burndown multiplier.
ADMIT = """
if redis.call('EXISTS', KEYS[6]) == 1 then return -1 end
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
local expired = redis.call('ZRANGEBYSCORE', KEYS[2], '-inf', now)
for _, id in ipairs(expired) do redis.call('HDEL', KEYS[3], id) end
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', now)
redis.call('ZREMRANGEBYSCORE', KEYS[4], '-inf', now - 60)
if redis.call('EXISTS', KEYS[5]) == 1 then return 0 end
if redis.call('ZCARD', KEYS[1]) >= tonumber(ARGV[2]) then return 0 end
if redis.call('ZCARD', KEYS[4]) >= tonumber(ARGV[3]) then return 0 end
local charged = 0
for _, cost in ipairs(redis.call('HVALS', KEYS[3])) do charged = charged + tonumber(cost) end
if charged + tonumber(ARGV[4]) > tonumber(ARGV[5]) then return 0 end
redis.call('ZADD', KEYS[1], now + tonumber(ARGV[6]), ARGV[1])
redis.call('ZADD', KEYS[2], now + tonumber(ARGV[6]), ARGV[1])
redis.call('HSET', KEYS[3], ARGV[1], ARGV[4])
redis.call('ZADD', KEYS[4], now, ARGV[1])
for i = 1, 4 do redis.call('EXPIRE', KEYS[i], tonumber(ARGV[6]) + 120) end
return 1
"""

SETTLE = """
local now = tonumber(redis.call('TIME')[1])
redis.call('ZREM', KEYS[1], ARGV[1])
redis.call('ZADD', KEYS[2], now + 60, ARGV[1])
redis.call('HSET', KEYS[3], ARGV[1], ARGV[2])
"""

RENEW = """
local now = tonumber(redis.call('TIME')[1])
if redis.call('ZSCORE', KEYS[1], ARGV[1]) then
 redis.call('ZADD', KEYS[1], 'XX', now + tonumber(ARGV[2]), ARGV[1])
 redis.call('ZADD', KEYS[2], 'XX', now + tonumber(ARGV[2]), ARGV[1])
end
"""


def model_key(model_id: str) -> str:
    # Geo/global profiles of the same model share the application's budget.
    return re.sub(r"^(global|us|eu|apac)\.", "", model_id)


def model_limits(model_id: str) -> dict[str, int]:
    settings = get_settings()
    overrides = json.loads(settings.bedrock_model_limits)
    rule = overrides.get(model_key(model_id), {})
    return {
        "rpm": max(1, int(rule.get("rpm", settings.bedrock_requests_per_minute))),
        "tpm": max(1, int(rule.get("tpm", settings.bedrock_tokens_per_minute))),
        "burndown": max(
            1, int(rule.get("burndown", 5 if "anthropic." in model_id else 1))
        ),
    }


class RequestBudget:
    def __init__(self, reserved: int, burndown: int):
        # Unknown network failures retain the entire reservation conservatively.
        self.charged = reserved
        self.burndown = burndown

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        self.charged = max(0, input_tokens) + max(0, output_tokens) * self.burndown


@asynccontextmanager
async def bedrock_request_budget(
    model_id: str, input_upper_bound: int, max_tokens: int
):
    settings = get_settings()
    limits = model_limits(model_id)
    reserved = input_upper_bound + max_tokens * limits["burndown"]
    if reserved > limits["tpm"]:
        raise ValueError(
            f"Request exceeds configured token budget for {model_id}; needs {reserved}, budget {limits['tpm']}"
        )
    client = redis.from_url(settings.celery_broker_url, decode_responses=True)
    prefix = f"lenquant:bedrock:{model_key(model_id)}"
    keys = [
        "lenquant:bedrock:active",
        prefix + ":budgets",
        prefix + ":costs",
        prefix + ":requests",
        prefix + ":cooldown",
        prefix + ":daily-quota",
    ]
    lease_id = uuid4().hex
    ttl = max(1200, settings.bedrock_timeout_seconds * 2 + 60)
    budget = RequestBudget(reserved, limits["burndown"])
    heartbeat = None
    acquired = False
    try:
        while True:
            admission = await client.eval(
                ADMIT,
                len(keys),
                *keys,
                lease_id,
                max(1, settings.bedrock_max_concurrent),
                limits["rpm"],
                reserved,
                limits["tpm"],
                ttl,
            )
            if admission == -1:
                raise RuntimeError(
                    f"Daily token quota unavailable for {model_id}; use fallback"
                )
            if admission == 1:
                break
            await asyncio.sleep(1)
        acquired = True

        async def renew():
            while True:
                await asyncio.sleep(30)
                await client.eval(RENEW, 2, *keys[:2], lease_id, ttl)

        heartbeat = asyncio.create_task(renew())
        yield budget
    finally:
        if heartbeat:
            heartbeat.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await heartbeat
        try:
            if acquired:
                await client.eval(SETTLE, 3, *keys[:3], lease_id, budget.charged)
        finally:
            await client.aclose()


async def throttle_cooldown(model_id: str, seconds: int = 60) -> None:
    client = redis.from_url(get_settings().celery_broker_url, decode_responses=True)
    try:
        await client.set(
            f"lenquant:bedrock:{model_key(model_id)}:cooldown", "1", ex=seconds
        )
    finally:
        await client.aclose()


async def mark_daily_quota_exhausted(model_id: str, seconds: int = 3600) -> None:
    # AWS does not expose the reset time in this error. Probe again after an
    # hour; all workers use the fallback immediately in the meantime.
    client = redis.from_url(get_settings().celery_broker_url, decode_responses=True)
    try:
        await client.set(
            f"lenquant:bedrock:{model_key(model_id)}:daily-quota", "1", ex=seconds
        )
    finally:
        await client.aclose()
