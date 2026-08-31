from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
import boto3

from app.core.celery_app import celery_app
from app.core.leads import lead_repository
from app.core.sites import site_repository
from app.core.screenshot_analyzer import get_screenshot_analyzer
from app.schemas.site import SiteGenerateRequest
from app.core.asset_retention import AssetRetentionManager

logger = logging.getLogger(__name__)


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
    acks_late=True,
    reject_on_worker_lost=True,
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
                    error_message=f"Extraction failed: {str(exc).splitlines()[0]}. Retry {self.request.retries}/{self.max_retries}",
                    finished=self.request.retries >= self.max_retries,
                )
            )
        except Exception:
            pass  # Best effort
        raise


@celery_app.task(
    name="lenquant.jobs.run_site_generation",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
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
        # Best-effort: queue screenshot capture after generation completes.
        site = await site_repository.get_site(site_id)
        if site and site.previewUrl:
            try:
                run_screenshot_task.delay(site_id=site.id, preview_url=site.previewUrl)  # type: ignore[attr-defined]
            except Exception as exc:
                logging.warning(
                    "Could not queue screenshot task for site %s: %s", site.id, exc
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


@celery_app.task(
    name="lenquant.jobs.run_site_republish",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=2,
)
def run_site_republish_task(self, site_id: str, job_id: str) -> None:
    """Recompile and re-upload existing site without regenerating via LLM."""

    async def runner() -> None:
        await site_repository.run_republish_job(site_id=site_id, job_id=job_id)
        site = await site_repository.get_site(site_id)
        if site and site.previewUrl:
            try:
                run_screenshot_task.delay(site_id=site.id, preview_url=site.previewUrl)  # type: ignore[attr-defined]
            except Exception as exc:
                logging.warning(
                    "Could not queue screenshot task for site %s: %s", site.id, exc
                )

    try:
        _run(runner())
    except Exception:
        logging.error(
            f"Site republish failed for site {site_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        raise


@celery_app.task(
    name="lenquant.jobs.run_analysis_refresh",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=2,
)
def run_analysis_refresh_task(self, lead_id: str, job_id: str) -> None:
    """Run analysis refresh on existing extraction data."""
    try:
        _run(lead_repository.run_analysis_refresh_job(lead_id=lead_id, job_id=job_id))
    except Exception:
        import logging

        logging.error(
            f"Analysis refresh failed for lead {lead_id}, job {job_id}. "
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


@celery_app.task(
    name="lenquant.jobs.run_screenshot",
    bind=True,
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=120,
)
def run_screenshot_task(self, site_id: str, preview_url: str) -> None:
    """Capture a viewport screenshot for a generated site and persist it to MongoDB."""

    async def _async_runner() -> None:
        from app.core.config import get_settings
        from app.core.mongo import get_database
        from app.core.site_screenshot import capture_site_screenshot

        preview_base_url = get_settings().preview_base_url

        # capture_site_screenshot is synchronous (uses Playwright sync API),
        # so we run it in a thread-pool executor to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None,
            capture_site_screenshot,
            site_id,
            preview_url,
            preview_base_url,
        )
        if metadata is None:
            logger.warning(
                "run_screenshot_task: capture returned None for site %s", site_id
            )
            return

        database = get_database()
        if database is None:
            logger.warning(
                "run_screenshot_task: no database available — cannot persist screenshot for site %s",
                site_id,
            )
            return

        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "screenshotRefs": [metadata.model_dump()],
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )
        # Screenshot capture is asynchronous with generation. Run visual QA
        # now, so the provisional fallback score is replaced when possible.
        try:
            settings = get_settings()
            s3_key = f"{settings.asset_s3_prefix or 'lenmanag/'}screenshots/{site_id}/preview.jpg"
            image = boto3.client(
                "s3", region_name=settings.asset_s3_region or "us-east-1"
            ).get_object(Bucket=settings.asset_s3_bucket, Key=s3_key)["Body"].read()
            site = await site_repository.get_site(site_id)
            if site is not None:
                qa = await get_screenshot_analyzer().perform_qa_analysis(
                    site_id=site_id,
                    desktop_screenshot=image,
                    extraction_summary="Generated preview page",
                    section_stack=[section.title for section in site.sectionStack],
                    quality_threshold=settings.visual_redesign_quality_threshold,
                )
                if qa.get("available") and qa.get("qualityScore") is not None:
                    await site_repository.persist_visual_quality(
                        site_id, int(qa["qualityScore"]), qa
                    )
                    logger.info(
                        "run_screenshot_task: visual quality %.0f persisted for %s",
                        qa["qualityScore"], site_id,
                    )
                else:
                    logger.info("run_screenshot_task: visual QA unavailable for %s; retaining fallback", site_id)
        except Exception as exc:
            logger.warning("run_screenshot_task: visual QA unavailable for %s: %s", site_id, exc)
        logger.info(
            "run_screenshot_task: screenshot captured and saved for site %s", site_id
        )

    try:
        _run(_async_runner())
    except Exception as exc:
        logger.error(
            "run_screenshot_task: failed for site %s: %s",
            site_id,
            exc,
            exc_info=True,
        )
        raise


@celery_app.task(
    name="lenquant.jobs.run_multi_variant_generation",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=1800,  # 30 minutes max
    retry_jitter=True,
    max_retries=2,
)
def run_multi_variant_generation_task(
    self,
    lead_id: str,
    job_id: str,
    generation_types: list[str],
) -> None:
    """
    Generate multiple site variants for a lead.

    Uses distributed lock to ensure sequential execution globally.
    Each variant generation is atomic and sequential.
    """
    try:
        _run(_run_multi_variant_generation_async(lead_id, job_id, generation_types))
    except Exception as exc:
        logger.error(
            f"Multi-variant generation failed for lead {lead_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        # Update job status
        try:
            _run(
                lead_repository._update_job(
                    job_id=job_id,
                    status="failed",
                    error_message=f"Generation failed: {str(exc).splitlines()[0]}",
                    finished=self.request.retries >= self.max_retries,
                )
            )
        except Exception:
            pass
        raise


async def _run_multi_variant_generation_async(
    lead_id: str,
    job_id: str,
    generation_types: list[str],
) -> None:
    """Async implementation of multi-variant generation."""
    import time

    from app.core.generation_lock import generation_lock
    from app.core.generation_metrics import (
        GenerationMetricsCollector,
        log_generation_complete,
        log_generation_start,
        log_variant_progress,
    )
    from app.core.variant_strategy import get_variant_strategies
    from app.schemas.lead import LeadPatchRequest
    from app.schemas.site import VariantType

    # Initialize metrics collector
    metrics_collector = GenerationMetricsCollector()
    generation_start_time = time.monotonic()

    # Get lead and extraction (shared across all variants)
    lead = await lead_repository.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    extraction = await lead_repository.get_extraction(lead_id)
    if not extraction or extraction.version <= 0:
        raise ValueError(f"Extraction not available for lead {lead_id}")

    analysis = await lead_repository.get_analysis(lead_id)

    # Get variant strategies - industry from lead or analysis
    industry = lead.industry
    if not industry and analysis and hasattr(analysis, "analysis"):
        # ExtractionAnalysisResponse wraps ExtractionAnalysis
        industry = getattr(analysis.analysis, "industry", None)
    strategies = get_variant_strategies(industry)

    # Log generation start
    total_variants = len(generation_types)
    log_generation_start(lead_id, generation_types, total_variants)

    # Generate each variant sequentially with distributed lock
    generated_sites = []
    failed_variants = 0

    for i, variant_type_str in enumerate(generation_types):
        # Cast to VariantType for type safety
        variant_type: VariantType = variant_type_str  # type: ignore[assignment]

        # Log progress
        log_variant_progress(lead_id, variant_type_str, i + 1, total_variants)

        # Update job progress
        progress = int((i / total_variants) * 100)
        await lead_repository._update_job(
            job_id=job_id,
            status="running",
            progress=progress,
            step=f"Generating {variant_type} ({i + 1}/{total_variants})",
        )

        # Log pipeline event for variant progress
        await lead_repository.log_pipeline_event(
            lead_id,
            event_type="site_generation_progress",
            status="info",
            message=f"Generating {variant_type} variant",
            detail=f"Variant {i + 1} of {total_variants}",
            job_id=job_id,
            variant_type=variant_type_str,
            metadata={"variantIndex": i + 1, "totalVariants": total_variants},
        )

        # Track this variant's metrics
        async with metrics_collector.track_generation(
            lead_id, variant_type_str
        ) as metrics:
            try:
                # Track lock wait time
                lock_start = time.monotonic()

                # Acquire global lock and generate
                async with generation_lock(timeout_seconds=600):  # 10 min timeout
                    metrics.lock_wait_seconds = time.monotonic() - lock_start

                    logger.info(
                        f"Generating variant {variant_type} for lead {lead_id} "
                        f"(lock_wait={metrics.lock_wait_seconds:.1f}s)"
                    )

                    # Get strategy for this variant type (cast for dict lookup)
                    strategy = strategies.get(variant_type)  # type: ignore[arg-type]
                    if not strategy and variant_type_str == "nextjs":
                        # NextJS uses default strategy
                        strategy = {
                            "variantType": "nextjs",
                            "variantLabel": "Next.js Site",
                            "variantPosition": 4,
                            "designMode": "interactive",
                            "paletteMode": "zinc",
                            "creativeBriefGuidance": "",
                            "inspirationKeywords": [],
                            "avoidPatterns": [],
                        }

                    if not strategy:
                        logger.warning(f"Unknown variant type {variant_type}, skipping")
                        metrics.success = False
                        metrics.error_message = "Unknown variant type"
                        failed_variants += 1
                        continue

                    site = await site_repository.generate_site_variant(
                        lead_id=lead_id,
                        variant_type=variant_type,
                        variant_strategy=dict(strategy),
                        extraction=extraction,
                        analysis=analysis,
                        user_id=lead.user_id,
                    )

                    generated_sites.append(site)
                    metrics.success = True
                    metrics.model_used = "bedrock"  # TODO: Track actual model

                    # Log pipeline event for variant completed
                    variant_time_ms = int(
                        (time.monotonic() - lock_start - metrics.lock_wait_seconds)
                        * 1000
                    )
                    await lead_repository.log_pipeline_event(
                        lead_id,
                        event_type="site_variant_generated",
                        status="success",
                        message=f"{variant_type} variant generated",
                        detail=f"Quality score: {site.qualityScore}%",
                        job_id=job_id,
                        variant_type=variant_type_str,
                        duration_ms=variant_time_ms,
                        metadata={
                            "qualityScore": site.qualityScore,
                            "previewSlug": site.previewSlug,
                        },
                    )

                    logger.info(
                        f"Variant {variant_type} completed ({i + 1}/{total_variants}): "
                        f"{site.previewUrl}"
                    )

            except Exception as e:
                import traceback

                logger.error(
                    f"Variant {variant_type} failed for lead {lead_id}: {e}",
                    exc_info=True,
                )
                metrics.success = False
                metrics.error_message = str(e)
                failed_variants += 1

                # Capture full error details
                error_type = type(e).__name__
                error_msg = str(e)
                tb_lines = traceback.format_exc().split("\n")[-6:]
                tb_summary = "\n".join(tb_lines).strip()

                # Log pipeline event for variant failure with full traceback
                await lead_repository.log_pipeline_event(
                    lead_id,
                    event_type="site_generation_failed",
                    status="error",
                    message=f"{variant_type} variant failed: {error_type}",
                    detail=f"{error_msg}\n\nTraceback:\n{tb_summary}",
                    job_id=job_id,
                    variant_type=variant_type_str,
                    metadata={"errorType": error_type, "errorMessage": error_msg},
                )
                # Continue with next variant instead of failing entire job

    # Log metrics summary
    total_time = time.monotonic() - generation_start_time
    total_time_ms = int(total_time * 1000)
    metrics_collector.log_summary()
    log_generation_complete(
        lead_id,
        successful=len(generated_sites),
        failed=failed_variants,
        total_seconds=total_time,
    )

    # Mark job complete
    await lead_repository._update_job(
        job_id=job_id,
        status="completed",
        progress=100,
        step=f"Generated {len(generated_sites)}/{total_variants} variants",
        finished=True,
    )

    # Log final pipeline event
    if generated_sites:
        avg_quality = sum(s.qualityScore for s in generated_sites) // len(
            generated_sites
        )
        await lead_repository.log_pipeline_event(
            lead_id,
            event_type="site_generation_completed",
            status="success",
            message=f"Generated {len(generated_sites)} variant(s)",
            detail=f"Average quality: {avg_quality}%, {failed_variants} failed",
            job_id=job_id,
            duration_ms=total_time_ms,
            metadata={
                "successCount": len(generated_sites),
                "failedCount": failed_variants,
                "averageQuality": avg_quality,
            },
        )
    else:
        await lead_repository.log_pipeline_event(
            lead_id,
            event_type="site_generation_failed",
            status="error",
            message="All variants failed to generate",
            detail=f"Attempted {total_variants} variant(s)",
            job_id=job_id,
            duration_ms=total_time_ms,
            metadata={"failedCount": failed_variants},
        )

    # Update lead pipeline stage (only if at least one succeeded)
    if generated_sites:
        await lead_repository.update_lead(
            lead_id,
            LeadPatchRequest(pipelineStage="ready"),
        )
    else:
        await lead_repository.update_lead(
            lead_id,
            LeadPatchRequest(pipelineStage="needs_attention"),
        )

    # Best-effort: queue a screenshot task for each successfully generated site.
    # Failures here must never block or fail the generation job.
    for site in generated_sites:
        try:
            run_screenshot_task.delay(site_id=site.id, preview_url=site.previewUrl)  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning(
                "Could not queue screenshot task for site %s: %s", site.id, exc
            )

    logger.info(
        f"Multi-variant generation completed for lead {lead_id}: "
        f"{len(generated_sites)} sites generated, {failed_variants} failed, "
        f"total_time={total_time:.1f}s"
    )


@celery_app.task(
    name="lenquant.jobs.run_site_refinement",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=2,
)
def run_site_refinement_job_task(
    self, site_id: str, job_id: str, prompt_id: str
) -> None:
    """Apply targeted operator refinement to existing site source code."""

    async def runner() -> None:
        await site_repository.run_refinement_job(
            site_id=site_id, job_id=job_id, prompt_id=prompt_id
        )
        site = await site_repository.get_site(site_id)
        if site and site.previewUrl:
            try:
                run_screenshot_task.delay(site_id=site.id, preview_url=site.previewUrl)  # type: ignore[attr-defined]
            except Exception as exc:
                logging.warning(
                    "Could not queue screenshot task for site %s: %s", site.id, exc
                )

    try:
        _run(runner())
    except Exception:
        logging.error(
            f"Site refinement failed for site {site_id}, job {job_id}. "
            f"Retry {self.request.retries}/{self.max_retries}",
            exc_info=True,
        )
        raise
