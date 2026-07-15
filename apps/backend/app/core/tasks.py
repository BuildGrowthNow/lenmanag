from __future__ import annotations

import asyncio

from app.core.celery_app import celery_app
from app.core.leads import lead_repository
from app.core.sites import site_repository
from app.schemas.site import SiteGenerateRequest
from app.core.asset_retention import AssetRetentionManager



def _run(coro):
    """Run async coroutine in a fresh event loop to avoid 'Event loop is closed' errors in Celery workers."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="lenquant.jobs.run_extraction")
def run_extraction_job_task(lead_id: str, job_id: str, refresh: bool) -> None:
    _run(lead_repository.run_extraction_job(lead_id=lead_id, job_id=job_id, refresh=refresh))


@celery_app.task(name="lenquant.jobs.run_site_generation")
def run_site_generation_job_task(site_id: str, job_id: str, request_payload: dict | None = None) -> None:
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

    _run(runner())


@celery_app.task(name="lenquant.jobs.purge_expired_assets")
def purge_expired_assets_task() -> dict:
    mgr = AssetRetentionManager()
    result = mgr.purge_expired_assets()
    return {"purged_count": result.purged_count, "purged_bytes": result.purged_bytes, "errors": result.errors}
