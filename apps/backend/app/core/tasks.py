from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.core.leads import lead_repository
from app.core.sites import site_repository
from app.schemas.site import SiteGenerateRequest
from app.core.asset_retention import AssetRetentionManager


def _run(coro):
    """Run async coroutine in a fresh event loop to avoid 'Event loop is closed' errors in Celery workers.

    With solo pool configured in celery_app.py, this should work reliably without crashes.
    """
    try:
        # Try to get existing event loop first (works with solo pool)
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        # No event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        # Log the error but don't close the loop in solo pool mode
        import logging

        logging.error(f"Task execution failed: {e}", exc_info=True)
        raise


@celery_app.task(
    name="lenquant.jobs.run_extraction",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes max
    retry_jitter=True,
    max_retries=3,
)
def run_extraction_job_task(self, lead_id: str, job_id: str, refresh: bool) -> None:
    """Run extraction job with automatic retry on failure.

    Retry policy:
    - Max 3 retries
    - Exponential backoff with jitter
    - Max backoff: 10 minutes
    """
    try:
        _run(
            lead_repository.run_extraction_job(
                lead_id=lead_id, job_id=job_id, refresh=refresh
            )
        )
    except Exception as exc:
        # Log failure with context
        import logging

        logging.error(
            f"Extraction job failed for lead {lead_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        # Update job status to reflect failure
        try:
            _run(
                lead_repository._update_job(
                    job_id=job_id,
                    status="failed",
                    error_message=f"Extraction failed: {str(exc)}. Retry {self.request.retries}/{self.max_retries}",
                    finished=self.request.retries >= self.max_retries,
                )
            )
        except Exception:
            pass  # Best effort
        raise


@celery_app.task(
    name="lenquant.jobs.run_site_generation",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=900,  # 15 minutes max
    retry_jitter=True,
    max_retries=2,
)
def run_site_generation_job_task(
    self, site_id: str, job_id: str, request_payload: dict | None = None
) -> None:
    """Run site generation job with automatic retry on failure.

    Retry policy:
    - Max 2 retries (generation is expensive)
    - Exponential backoff with jitter
    - Max backoff: 15 minutes
    """
    request = SiteGenerateRequest(**request_payload) if request_payload else None

    async def runner() -> None:
        # Run the primary generation job
        await site_repository.run_generation_job(
            site_id=site_id, job_id=job_id, request=request
        )
        # Best-effort scheduling of an automatic refinement pass when
        # screenshot QA fails the strict visual threshold.
        await site_repository._maybe_queue_auto_iteration(
            site_id=site_id, job_id=job_id, request=request
        )

    try:
        _run(runner())
    except Exception:
        # Log failure with context
        import logging

        logging.error(
            f"Site generation failed for site {site_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        raise


@celery_app.task(name="lenquant.jobs.purge_expired_assets")
def purge_expired_assets_task() -> dict:
    mgr = AssetRetentionManager()
    result = mgr.purge_expired_assets()
    return {
        "purged_count": result.purged_count,
        "purged_bytes": result.purged_bytes,
        "errors": result.errors,
    }
