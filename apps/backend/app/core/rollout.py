"""Deterministic rollout and quality-gate helpers for enhanced HTML."""

from __future__ import annotations

import hashlib
from typing import Any


def rollout_bucket(subject_id: str) -> int:
    return int(hashlib.sha256(subject_id.encode()).hexdigest()[:8], 16) % 100


def enhanced_html_enabled(subject_id: str, percentage: int) -> bool:
    return max(0, min(100, percentage)) > rollout_bucket(subject_id)


def should_rollback(
    metrics: dict[str, Any],
    *,
    failure_threshold: float = 0.05,
    latency_budget_seconds: float | None = None,
) -> bool:
    total = int(metrics.get("totalRuns", 0) or 0)
    failures = int(metrics.get("hardFailures", 0) or 0)
    if total >= 20 and failures / total > failure_threshold:
        return True
    if latency_budget_seconds is not None:
        p95 = float(metrics.get("p95LatencySeconds", 0) or 0)
        if total >= 20 and p95 > latency_budget_seconds:
            return True
    return bool(metrics.get("performanceBudgetRegression"))


def rollout_decision(
    subject_id: str,
    percentage: int,
    *,
    metrics: dict[str, Any] | None = None,
    failure_threshold: float = 0.05,
    latency_budget_seconds: float | None = None,
) -> dict[str, Any]:
    """Return an auditable enable/hold decision for one rollout subject."""
    bucket = rollout_bucket(subject_id)
    configured = max(0, min(100, percentage)) > bucket
    rollback = should_rollback(
        metrics or {},
        failure_threshold=failure_threshold,
        latency_budget_seconds=latency_budget_seconds,
    )
    reasons: list[str] = []
    if not configured:
        reasons.append("outside_percentage")
    if rollback:
        reasons.append("quality_or_performance_regression")
    return {
        "enabled": configured and not rollback,
        "bucket": bucket,
        "percentage": max(0, min(100, percentage)),
        "rollback": rollback,
        "reasons": reasons,
    }


def publish_allowed(decision: dict[str, Any], *, shadow_mode: bool) -> bool:
    """Shadow execution may collect artifacts/QA but can never publish them."""
    return bool(decision.get("enabled")) and not shadow_mode
