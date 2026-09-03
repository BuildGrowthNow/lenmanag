from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any
import boto3

from app.core.celery_app import celery_app
from app.core.leads import lead_repository
from app.core.sites import is_artifact_generated_site, site_repository
from app.core.screenshot_analyzer import get_screenshot_analyzer
from app.core.site_quality_metrics import QUALITY_GATES, build_quality_gate_report
from app.schemas.site import SiteGenerateRequest
from app.core.asset_retention import AssetRetentionManager

logger = logging.getLogger(__name__)


def _structured_generation_error(error: Exception, variant_type: str) -> dict[str, Any]:
    """Return a safe operator-facing error without prompts, secrets, or tracebacks."""
    from app.core.config import get_settings
    from app.core.static_html_generator import StaticGenerationError

    if isinstance(error, StaticGenerationError):
        stage = error.stage
        code = error.code
        message = str(error)
        rule_id = error.rule_id
        context = error.context
    else:
        stage = "generation"
        code = "variant_generation_failed"
        message = str(error).splitlines()[0] or type(error).__name__
        rule_id = code
        context = {}
    return {
        "variantType": variant_type,
        "stage": stage,
        "errorCode": code,
        "ruleId": rule_id,
        "context": context,
        "message": message[:500],
        "provider": (get_settings().llm_provider or "unknown").lower(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


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
    self,
    site_id: str,
    job_id: str,
    request_payload: dict | None = None,
    generation_run_id: str | None = None,
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
            site_id=site_id,
            job_id=job_id,
            request=request,
            generation_run_id=generation_run_id,
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
                await capture_screenshot(site_id=site.id, preview_url=site.previewUrl)
            except Exception as exc:
                logging.warning(
                    "Could not capture screenshot for site %s: %s", site.id, exc
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
                await capture_screenshot(site_id=site.id, preview_url=site.previewUrl)
            except Exception as exc:
                logging.warning(
                    "Could not capture screenshot for site %s: %s", site.id, exc
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


async def capture_screenshot(
    site_id: str, preview_url: str, generation_run_id: str | None = None
) -> None:
    """Capture a viewport screenshot and persist its runtime QA result.

    This is deliberately an async function so workerless deployments never try
    to run a Celery eager task inside the event loop that generated the site.
    """

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
            if generation_run_id:
                await _record_runtime_qa_result(generation_run_id, site_id, "failed")
            database = get_database()
            if database is not None:
                await database["generated_sites"].update_one(
                    {"id": site_id},
                    {
                        "$set": {
                            "qaStatus": "fail",
                            "readinessStatus": "blocked",
                            "updatedAt": datetime.now(timezone.utc),
                        }
                    },
                )
            return

        database = get_database()
        if database is None:
            logger.warning(
                "run_screenshot_task: no database available — cannot persist screenshot for site %s",
                site_id,
            )
            if generation_run_id:
                await _record_runtime_qa_result(generation_run_id, site_id, "failed")
            return

        try:
            runtime_qa = json.loads(metadata.notes or "{}")
        except (TypeError, ValueError):
            runtime_qa = {}
        interactions = runtime_qa.get("interactions") or []
        semantic_measured = (
            "missingFooter" in runtime_qa or "emptyMediaRegions" in runtime_qa
        )
        mobile_menu = runtime_qa.get("mobileMenu")
        performance_measured = "horizontalOverflow" in runtime_qa
        runtime_gates = {name: None for name in QUALITY_GATES}
        runtime_gates.update(
            {
                "semanticCompleteness": (
                    not runtime_qa.get("missingFooter")
                    and not runtime_qa.get("emptyMediaRegions"),
                )
                if semantic_measured
                else None,
                "interactionReliability": all(
                    item.get("passed") for item in interactions
                )
                if interactions
                else None,
                "accessibility": mobile_menu != "failed"
                if mobile_menu in {"passed", "failed"}
                else None,
                "performance": not runtime_qa.get("horizontalOverflow")
                if performance_measured
                else None,
            }
        )
        quality_gate_report = build_quality_gate_report(runtime_gates)

        await database["generated_sites"].update_one(
            {"id": site_id},
            {
                "$set": {
                    "screenshotRefs": [metadata.model_dump()],
                    # Runtime health is authoritative. A captured screenshot is
                    # not evidence that the generated application works.
                    "qaStatus": "fail"
                    if _metadata_has_fatal_runtime_failure(metadata)
                    else "warn",
                    "readinessStatus": "blocked"
                    if _metadata_has_fatal_runtime_failure(metadata)
                    else "ready_for_review",
                    "runtimeQA": runtime_qa,
                    "qualityGateReport": quality_gate_report,
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
        )
        # Screenshot capture is asynchronous with generation. Run visual QA
        # now, so the provisional fallback score is replaced when possible.
        try:
            settings = get_settings()
            s3_key = f"{settings.asset_s3_prefix or 'lenmanag/'}screenshots/{site_id}/preview.jpg"
            image = (
                boto3.client("s3", region_name=settings.asset_s3_region or "us-east-1")
                .get_object(Bucket=settings.asset_s3_bucket, Key=s3_key)["Body"]
                .read()
            )
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
                    try:
                        runtime_qa = json.loads(metadata.notes or "{}")
                    except (TypeError, ValueError):
                        runtime_qa = {}
                    qa["runtimeQA"] = runtime_qa
                    qa["qualityGateReport"] = quality_gate_report
                    await site_repository.persist_visual_quality(
                        site_id, int(qa["qualityScore"]), qa
                    )
                    logger.info(
                        "run_screenshot_task: visual quality %.0f persisted for %s",
                        qa["qualityScore"],
                        site_id,
                    )
                else:
                    logger.info(
                        "run_screenshot_task: visual QA unavailable for %s; retaining fallback",
                        site_id,
                    )
        except Exception as exc:
            logger.warning(
                "run_screenshot_task: visual QA unavailable for %s: %s", site_id, exc
            )
        logger.info(
            "run_screenshot_task: screenshot captured and saved for site %s", site_id
        )
        if generation_run_id:
            await _record_runtime_qa_result(
                generation_run_id,
                site_id,
                "failed"
                if _metadata_has_fatal_runtime_failure(metadata)
                else "completed",
            )

    await _async_runner()


@celery_app.task(
    name="lenquant.jobs.run_screenshot",
    bind=True,
    max_retries=2,
    retry_backoff=True,
    retry_backoff_max=120,
)
def run_screenshot_task(
    self, site_id: str, preview_url: str, generation_run_id: str | None = None
) -> None:
    """Legacy Celery entrypoint retained for compatibility with existing jobs."""

    try:
        _run(capture_screenshot(site_id, preview_url, generation_run_id))
    except Exception as exc:
        logger.error(
            "run_screenshot_task: failed for site %s: %s",
            site_id,
            exc,
            exc_info=True,
        )
        if generation_run_id and self.request.retries >= self.max_retries:
            try:
                _run(_record_runtime_qa_result(generation_run_id, site_id, "failed"))
            except Exception:
                logger.exception("Could not record failed runtime QA for %s", site_id)
        raise


async def _record_runtime_qa_result(run_id: str, site_id: str, status: str) -> None:
    """Record one variant QA result and close the run only after all QA completes."""
    run = await site_repository._get_generation_run(run_id)
    if not run or run.get("status") in {
        "superseded",
        "cancelled",
        "completed",
        "failed",
    }:
        return
    results = [dict(item) for item in run.get("variantResults", [])]
    for item in results:
        if item.get("siteId") == site_id:
            item["status"] = status
    await site_repository._update_generation_run(run_id, {"variantResults": results})
    refreshed = await site_repository._get_generation_run(run_id)
    if not refreshed:
        return
    terminal = {"completed", "failed"}
    if results and all(
        item.get("status") in terminal for item in refreshed.get("variantResults", [])
    ):
        failed = any(
            item.get("status") == "failed" for item in refreshed["variantResults"]
        )
        final_status = "completed" if not failed else "partial"
        await site_repository._update_generation_run(
            run_id,
            {"status": final_status, "finishedAt": datetime.now(timezone.utc)},
        )
        await lead_repository._update_job(
            refreshed["jobId"],
            status=final_status,
            progress=100,
            step="Runtime QA completed"
            if not failed
            else "Runtime QA found variant failures",
            error_message=None
            if not failed
            else "One or more variants failed generation or runtime QA.",
            finished=True,
        )
        await lead_repository.log_pipeline_event(
            refreshed["leadId"],
            event_type="site_generation_completed"
            if final_status == "completed"
            else "site_generation_failed",
            status="success" if final_status == "completed" else "error",
            message="Site generation completed"
            if final_status == "completed"
            else "Site generation requires attention",
            detail="All requested previews passed runtime QA."
            if final_status == "completed"
            else "One or more requested previews failed generation or runtime QA.",
            job_id=refreshed["jobId"],
            metadata={"status": final_status},
        )
        await site_repository._release_generation_input(
            lead_id=refreshed["leadId"],
            input_hash=refreshed["generationInputHash"],
            job_id=refreshed["jobId"],
        )
        await lead_repository.update_generation_stage_if_latest(
            refreshed["leadId"], run_id, "ready" if not failed else "needs_attention"
        )


def _metadata_has_fatal_runtime_failure(metadata: Any) -> bool:
    try:
        runtime = json.loads(metadata.notes or "{}")
    except (TypeError, ValueError):
        return True
    return (
        bool(runtime.get("fatalRuntimeFailures"))
        or runtime.get("runtimeStatus") == "failed"
    )


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
    generation_run_id: str | None = None,
) -> None:
    """
    Generate multiple site variants for a lead.

    Uses a distributed per-lead lock to ensure variants for one lead remain
    sequential while independent leads can generate concurrently.
    """
    try:
        _run(
            _run_multi_variant_generation_async(
                lead_id, job_id, generation_types, generation_run_id
            )
        )
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
    generation_run_id: str | None = None,
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
    from app.schemas.site import VariantType

    # Initialize metrics collector
    metrics_collector = GenerationMetricsCollector()
    generation_start_time = time.monotonic()

    run = (
        await site_repository._get_generation_run(generation_run_id)
        if generation_run_id
        else None
    )
    if run and run.get("status") in {"superseded", "cancelled"}:
        logger.info("Skipping superseded multi-variant run %s", generation_run_id)
        return
    # Resolve the immutable source-of-truth snapshot. Never fall back to latest
    # records once a run has been created.
    lead = await lead_repository.get_lead(lead_id)
    if not lead:
        raise ValueError(f"Lead {lead_id} not found")

    extraction = await (
        lead_repository.get_extraction_version(
            lead_id,
            run["snapshot"]["extractionId"],
            run["snapshot"]["extractionVersion"],
        )
        if run
        else lead_repository.get_extraction(lead_id)
    )
    if not extraction or extraction.version <= 0:
        raise ValueError(f"Extraction not available for lead {lead_id}")

    analysis = await (
        lead_repository.get_analysis_version(
            lead_id, run["snapshot"]["analysisId"], run["snapshot"]["analysisVersion"]
        )
        if run and run["snapshot"].get("analysisId")
        else lead_repository.get_analysis(lead_id)
    )
    approved_brief = await (
        lead_repository.get_master_brief_version(
            lead_id, run["snapshot"]["briefId"], run["snapshot"]["briefVersion"]
        )
        if run
        else lead_repository.get_master_brief(lead_id)
    )
    if run and (not approved_brief or approved_brief.approvalState != "approved"):
        raise ValueError("pinned_brief_not_approved")

    # Strategies are immutable run inputs; never recalculate them from the live lead.
    strategies = {
        item.get("variantType"): item
        for item in ((run or {}).get("snapshot", {}).get("variantStrategies") or [])
    }

    # Log generation start
    total_variants = len(generation_types)
    log_generation_start(lead_id, generation_types, total_variants)

    # Generate each variant sequentially with distributed lock
    generated_sites = []
    failed_variants = 0
    variant_results: list[dict[str, Any]] = []

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

                # Serialize variants for this lead while allowing other leads
                # to generate on separate workers.
                async with generation_lock(
                    timeout_seconds=600, scope=lead_id
                ):  # 10 min timeout
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
                        variant_results.append(
                            {
                                "variantType": variant_type_str,
                                "status": "failed",
                                "stage": "generation",
                                "errorCode": "unknown_variant_type",
                                "message": "Unknown variant type",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        continue

                    # A provider can return a transiently truncated or malformed
                    # artifact even when the prompt and validation contract are
                    # correct. Retry the individual variant once before declaring
                    # the whole multi-variant run partial. The generator itself
                    # still fails closed and never publishes an invalid artifact.
                    site = None
                    for variant_attempt in range(2):
                        try:
                            site = await site_repository.generate_site_variant(
                                lead_id=lead_id,
                                variant_type=variant_type,
                                variant_strategy=dict(strategy),
                                extraction=extraction,
                                analysis=analysis,
                                user_id=lead.user_id,
                                approved_brief=approved_brief,
                                generation_run_id=generation_run_id,
                            )
                            if not is_artifact_generated_site(site):
                                raise ValueError(
                                    "generated variant did not produce an artifact_generated preview"
                                )
                            break
                        except Exception:
                            if variant_attempt == 1:
                                raise
                            logger.warning(
                                "Variant %s failed on attempt 1; retrying once",
                                variant_type,
                                exc_info=True,
                            )

                    if site is None:
                        raise ValueError("variant generation returned no site")

                    generated_sites.append(site)
                    variant_results.append(
                        {
                            "variantType": variant_type_str,
                            "siteId": site.id,
                            "status": "runtime_qa",
                        }
                    )
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
                logger.error(
                    f"Variant {variant_type} failed for lead {lead_id}: {e}",
                    exc_info=True,
                )
                metrics.success = False
                structured_error = _structured_generation_error(e, variant_type_str)
                metrics.error_message = structured_error["message"]
                failed_variants += 1

                variant_results.append({**structured_error, "status": "failed"})

                # Only the safe structured error is exposed to operators.
                await lead_repository.log_pipeline_event(
                    lead_id,
                    event_type="site_generation_failed",
                    status="error",
                    message=f"{variant_type} generation failed",
                    detail=structured_error["message"],
                    job_id=job_id,
                    variant_type=variant_type_str,
                    metadata=structured_error,
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
    failure_summary = next(
        (
            str(item.get("message"))
            for item in variant_results
            if item.get("status") == "failed" and item.get("message")
        ),
        None,
    )

    # Keep the job open while generated previews undergo in-process runtime QA.
    # A job is completed only after every requested variant has a generated
    # artifact and runtime QA has completed.
    # and every runtime check has passed.
    if run and generated_sites:
        await lead_repository._update_job(
            job_id=job_id,
            status="running",
            progress=90,
            step=f"Runtime QA for {len(generated_sites)}/{total_variants} generated variants",
            error_message=failure_summary,
        )
    else:
        final_status = (
            "completed"
            if generated_sites and not failed_variants
            else ("partial" if generated_sites else "failed")
        )
        await lead_repository._update_job(
            job_id=job_id,
            status=final_status,
            progress=100,
            step=f"Generated {len(generated_sites)}/{total_variants} variants",
            error_message=None
            if final_status == "completed"
            else (failure_summary or "One or more variants failed generation."),
            finished=True,
        )

    # Log final pipeline event
    if generated_sites and not failed_variants:
        avg_quality = sum(s.qualityScore for s in generated_sites) // len(
            generated_sites
        )
        await lead_repository.log_pipeline_event(
            lead_id,
            event_type="site_generation_progress",
            status="info",
            message=f"Generated {len(generated_sites)} artifact(s); runtime QA pending",
            detail=f"Average source score: {avg_quality}%. Runtime QA is still required before completion.",
            job_id=job_id,
            duration_ms=total_time_ms,
            metadata={
                "successCount": len(generated_sites),
                "failedCount": 0,
                "averageQuality": avg_quality,
            },
        )
    elif generated_sites:
        await lead_repository.log_pipeline_event(
            lead_id,
            event_type="site_generation_failed",
            status="error",
            message=f"Generated {len(generated_sites)} artifact(s); {failed_variants} failed",
            detail="The failed variants were not published. Runtime QA is required before any artifact is usable.",
            job_id=job_id,
            duration_ms=total_time_ms,
            metadata={
                "successCount": len(generated_sites),
                "failedCount": failed_variants,
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

    if run:
        await site_repository._update_generation_run(
            generation_run_id,
            {
                "status": "runtime_qa" if generated_sites else "failed",
                "variantResults": variant_results,
            },
        )

    # Do not mark the lead ready until runtime QA has completed for every variant.
    if run and not generated_sites:
        await site_repository._update_generation_run(
            generation_run_id,
            {"status": "failed", "finishedAt": datetime.now(timezone.utc)},
        )
        await site_repository._release_generation_input(
            lead_id=lead_id, input_hash=run["generationInputHash"], job_id=run["jobId"]
        )
        await lead_repository.update_generation_stage_if_latest(
            lead_id, generation_run_id, "needs_attention"
        )

    # Run screenshot/runtime QA in-process. Production intentionally has no
    # worker or broker, and completion must not leave background work behind.
    for site in generated_sites:
        try:
            await capture_screenshot(
                site_id=site.id,
                preview_url=site.previewUrl,
                generation_run_id=generation_run_id,
            )
        except Exception as exc:
            logger.warning("Could not capture screenshot for site %s: %s", site.id, exc)
            if generation_run_id:
                await _record_runtime_qa_result(generation_run_id, site.id, "failed")

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
                await capture_screenshot(site_id=site.id, preview_url=site.previewUrl)
            except Exception as exc:
                logging.warning(
                    "Could not capture screenshot for site %s: %s", site.id, exc
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
