"""
Metrics tracking for multi-variant site generation.

Provides logging and metrics collection for:
- Generation throughput (variants per hour)
- Average time per variant
- Lock contention (wait times)
- Model fallback rate
- Failure rate by variant type
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncGenerator

logger = logging.getLogger(__name__)


@dataclass
class GenerationMetrics:
    """Metrics for a single variant generation."""

    lead_id: str
    variant_type: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    lock_wait_seconds: float = 0.0
    generation_seconds: float = 0.0
    model_used: str = ""
    fallback_count: int = 0
    success: bool = False
    error_message: str | None = None

    @property
    def total_seconds(self) -> float:
        """Total time including lock wait."""
        return self.lock_wait_seconds + self.generation_seconds

    def to_log_dict(self) -> dict:
        """Convert to dictionary for structured logging."""
        return {
            "lead_id": self.lead_id,
            "variant_type": self.variant_type,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "lock_wait_seconds": round(self.lock_wait_seconds, 2),
            "generation_seconds": round(self.generation_seconds, 2),
            "total_seconds": round(self.total_seconds, 2),
            "model_used": self.model_used,
            "fallback_count": self.fallback_count,
            "success": self.success,
            "error_message": self.error_message,
        }


class GenerationMetricsCollector:
    """
    Collects and logs metrics for multi-variant generation.

    Usage:
        collector = GenerationMetricsCollector()

        async with collector.track_generation("lead-123", "html_v1") as metrics:
            async with collector.track_lock_wait(metrics):
                async with generation_lock():
                    # do generation
                    pass
            metrics.model_used = "claude-sonnet"
            metrics.success = True

        collector.log_summary()
    """

    def __init__(self) -> None:
        self._metrics: list[GenerationMetrics] = []

    @asynccontextmanager
    async def track_generation(
        self, lead_id: str, variant_type: str
    ) -> AsyncGenerator[GenerationMetrics, None]:
        """Track a single variant generation."""
        metrics = GenerationMetrics(lead_id=lead_id, variant_type=variant_type)

        start_time = time.monotonic()

        try:
            yield metrics
        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            raise
        finally:
            metrics.completed_at = datetime.now(timezone.utc)
            metrics.generation_seconds = (
                time.monotonic() - start_time - metrics.lock_wait_seconds
            )

            self._metrics.append(metrics)

            # Log individual generation
            self._log_generation(metrics)

    @asynccontextmanager
    async def track_lock_wait(
        self, metrics: GenerationMetrics
    ) -> AsyncGenerator[None, None]:
        """Track time spent waiting for generation lock."""
        start_time = time.monotonic()

        try:
            yield
        finally:
            metrics.lock_wait_seconds = time.monotonic() - start_time

            if metrics.lock_wait_seconds > 30:
                logger.warning(
                    f"Long lock wait for {metrics.variant_type}: "
                    f"{metrics.lock_wait_seconds:.1f}s"
                )

    def _log_generation(self, metrics: GenerationMetrics) -> None:
        """Log individual generation metrics."""
        if metrics.success:
            logger.info(
                f"Generation completed: variant={metrics.variant_type} "
                f"lead={metrics.lead_id} "
                f"time={metrics.generation_seconds:.1f}s "
                f"lock_wait={metrics.lock_wait_seconds:.1f}s "
                f"model={metrics.model_used} "
                f"fallbacks={metrics.fallback_count}"
            )
        else:
            logger.error(
                f"Generation failed: variant={metrics.variant_type} "
                f"lead={metrics.lead_id} "
                f"time={metrics.generation_seconds:.1f}s "
                f"error={metrics.error_message}"
            )

    def log_summary(self) -> None:
        """Log summary of all generations in this batch."""
        if not self._metrics:
            return

        total = len(self._metrics)
        successful = sum(1 for m in self._metrics if m.success)
        failed = total - successful

        total_time = sum(m.total_seconds for m in self._metrics)
        total_lock_wait = sum(m.lock_wait_seconds for m in self._metrics)
        total_fallbacks = sum(m.fallback_count for m in self._metrics)

        avg_generation_time = (
            sum(m.generation_seconds for m in self._metrics if m.success) / successful
            if successful > 0
            else 0
        )

        # Count by variant type
        by_type: dict[str, dict] = {}
        for m in self._metrics:
            if m.variant_type not in by_type:
                by_type[m.variant_type] = {"success": 0, "failed": 0, "time": 0.0}
            if m.success:
                by_type[m.variant_type]["success"] += 1
                by_type[m.variant_type]["time"] += m.generation_seconds
            else:
                by_type[m.variant_type]["failed"] += 1

        logger.info(
            f"Multi-variant generation summary: "
            f"total={total} success={successful} failed={failed} "
            f"total_time={total_time:.1f}s avg_time={avg_generation_time:.1f}s "
            f"lock_wait={total_lock_wait:.1f}s fallbacks={total_fallbacks}"
        )

        for variant_type, stats in by_type.items():
            avg_time = stats["time"] / stats["success"] if stats["success"] > 0 else 0
            logger.info(
                f"  {variant_type}: success={stats['success']} "
                f"failed={stats['failed']} avg_time={avg_time:.1f}s"
            )

    def get_metrics(self) -> list[GenerationMetrics]:
        """Get all collected metrics."""
        return self._metrics.copy()


def log_lock_acquisition(elapsed_seconds: float) -> None:
    """Log generation lock acquisition."""
    if elapsed_seconds < 1:
        logger.info("Generation lock acquired immediately")
    elif elapsed_seconds < 30:
        logger.info(f"Generation lock acquired after {elapsed_seconds:.1f}s")
    else:
        logger.warning(
            f"Generation lock acquired after long wait: {elapsed_seconds:.1f}s"
        )


def log_model_fallback(
    primary_model: str,
    fallback_model: str,
    attempt: int,
    error: str,
) -> None:
    """Log model fallback event."""
    logger.warning(
        f"Model fallback: {primary_model} -> {fallback_model} "
        f"(attempt {attempt}): {error}"
    )


def log_generation_start(
    lead_id: str,
    variant_types: list[str],
    total_variants: int,
) -> None:
    """Log start of multi-variant generation."""
    logger.info(
        f"Starting multi-variant generation: lead={lead_id} "
        f"variants={variant_types} total={total_variants}"
    )


def log_generation_complete(
    lead_id: str,
    successful: int,
    failed: int,
    total_seconds: float,
) -> None:
    """Log completion of multi-variant generation."""
    if failed == 0:
        logger.info(
            f"Multi-variant generation completed: lead={lead_id} "
            f"generated={successful} time={total_seconds:.1f}s"
        )
    else:
        logger.warning(
            f"Multi-variant generation completed with failures: lead={lead_id} "
            f"success={successful} failed={failed} time={total_seconds:.1f}s"
        )


def log_variant_progress(
    lead_id: str,
    variant_type: str,
    current: int,
    total: int,
) -> None:
    """Log progress of variant generation."""
    logger.info(
        f"Generating variant: lead={lead_id} type={variant_type} "
        f"progress={current}/{total}"
    )
