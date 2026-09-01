from __future__ import annotations

import asyncio
import csv
import io
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from app.core.analytics import analytics_repository
from app.core.checkpoint import TaskCheckpoint, resume_or_start_task
from app.core.config import get_settings
from app.core.extraction import crawl_website
from app.core.extraction_analysis import analyze_extraction
from app.core.extraction_enrichment import (
    enrich_extraction,
    validate_extraction_content,
)
from app.core.mongo import get_database
from app.schemas.brief import (
    MasterBrief,
)
from app.schemas.extraction import (
    ExtractionAnalysis,
    ExtractionAnalysisResponse,
    ExtractionJobResponse,
    ExtractionSnapshot,
    ExtractionSummary,
    PageInventoryResponse,
)
from app.schemas.job import JobQueueHealthItem, JobQueueHealthResponse
from app.schemas.lead import (
    ImportRowResult,
    JobRetryRequest,
    JobSummary,
    LeadActionResponse,
    LeadDetail,
    LeadImportResponse,
    LeadListItem,
    LeadListResponse,
    LeadPatchRequest,
    LeadUpsertRequest,
    PipelineEvent,
    PipelineEventStatus,
    PipelineEventType,
    SourceReference,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _serialize_datetime(value: datetime | None) -> datetime | None:
    return _utc(value)


def _normalize_input_url(raw_url: str) -> tuple[str, str]:
    cleaned = raw_url.strip()
    if not cleaned:
        raise ValueError("website_url_required")

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", cleaned):
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    if not parsed.netloc:
        raise ValueError("website_url_invalid")

    hostname = parsed.hostname.lower() if parsed.hostname else ""
    if not hostname:
        raise ValueError("website_url_invalid")
    if hostname.startswith("www."):
        hostname = hostname[4:]

    normalized = parsed._replace(
        scheme=parsed.scheme.lower() or "https",
        netloc=hostname + (f":{parsed.port}" if parsed.port else ""),
        path=parsed.path.rstrip("/") or "",
        params="",
        query="",
        fragment="",
    )
    normalized_url = urlunparse(normalized)
    if normalized_url.endswith("/"):
        normalized_url = normalized_url[:-1]
    return normalized_url, hostname


def _missing_fields(lead: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not lead.get("companyName"):
        missing.append("companyName")
    if not lead.get("websiteUrl"):
        missing.append("websiteUrl")
    return missing


def _sanitize_section_title(title: str) -> str | None:
    """
    Convert internal section titles to public-friendly versions.
    Returns None if section should be dropped from public view.
    """
    lowered = title.lower().strip()

    # Direct mappings for internal terms
    mappings = {
        "brand cues": "Our Brand",
        "conversion path": "Get Started",
        "cta pattern": "Next Steps",
        "open questions": None,
        "missing requirements": None,
        "gap items": None,
        "services or offerings": "Services",
        "proof and trust": "Results",
        "about / point of view": "About",
        "packages or pricing": "Pricing",
        "work / gallery": "Portfolio",
        "contact path": "Contact",
    }

    if lowered in mappings:
        return mappings[lowered]

    # Drop sections with operator terms
    operator_terms = [
        "operator",
        "admin",
        "review",
        "gap",
        "missing",
        "requirements",
        "questions",
        "cues",
        "extraction",
        "source notes",
        "traceability",
    ]
    if any(term in lowered for term in operator_terms):
        return None

    # Return title with proper capitalization
    return title.title()


def _unique_by_key(items: list[dict[str, Any]], key_fn) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = key_fn(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _brief_reference_key(reference: dict[str, Any]) -> str:
    return "|".join(
        [
            str(reference.get("kind", "")),
            str(reference.get("sourceUrl", "")),
            str(reference.get("label", "")),
            str(reference.get("excerpt", "")),
            str(reference.get("confidence", "")),
            str(reference.get("evidenceType", "")),
            str(reference.get("assetType", "")),
        ]
    )


def _as_plain_dict(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else dict(value)


def _page_reference_from_citation(citation: dict[str, Any] | Any) -> dict[str, Any]:
    citation_data = _as_plain_dict(citation)
    return {
        "kind": "page",
        "sourceUrl": citation_data["pageUrl"],
        "label": citation_data["label"],
        "excerpt": citation_data["excerpt"],
        "confidence": int(citation_data.get("confidence", 0)),
        "evidenceType": citation_data.get("evidenceType"),
        "assetType": None,
    }


def _asset_reference_from_cue(cue: dict[str, Any] | Any) -> dict[str, Any]:
    cue_data = _as_plain_dict(cue)
    return {
        "kind": "asset",
        "sourceUrl": cue_data["sourceUrl"],
        "label": cue_data["label"],
        "excerpt": cue_data["value"],
        "confidence": int(cue_data.get("confidence", 0)),
        "evidenceType": None,
        "assetType": cue_data.get("assetType"),
    }


def _brief_asset_provenance(
    asset_cues: list[dict[str, Any] | Any],
) -> list[dict[str, Any]]:
    return _unique_by_key(
        [_asset_reference_from_cue(cue) for cue in asset_cues], _brief_reference_key
    )


def _normalized_row(row: dict[str, str]) -> dict[str, str]:
    return {
        str(key).strip().lower(): value for key, value in row.items() if key is not None
    }


def _lead_doc_to_detail(
    doc: dict[str, Any], jobs: list[dict[str, Any]] | None = None
) -> LeadDetail:
    latest_job = None
    if jobs:
        latest_job = _job_doc_to_summary(jobs[0])

    # Parse pipeline events, sorted by timestamp descending (newest first)
    raw_events = doc.get("pipelineEvents", [])
    pipeline_events = [_pipeline_event_to_model(e) for e in raw_events]
    pipeline_events.sort(key=lambda e: e.timestamp, reverse=True)

    return LeadDetail(
        id=str(doc["id"]),
        user_id=str(doc.get("user_id", "")),
        sourceType=doc["sourceType"],
        sourceRef=doc.get("sourceRef"),
        sourceRefs=[
            SourceReference(
                sourceType=item["sourceType"],
                sourceRef=item.get("sourceRef"),
                importedAt=_utc(item["importedAt"]) or _now(),
            )
            for item in doc.get("sourceRefs", [])
        ],
        companyName=doc.get("companyName"),
        contactName=doc.get("contactName"),
        websiteUrl=doc["websiteUrl"],
        normalizedWebsiteUrl=doc["normalizedWebsiteUrl"],
        normalizedDomain=doc["normalizedDomain"],
        detectedWebsiteUrl=doc.get("detectedWebsiteUrl"),
        status=doc["status"],
        pipelineStage=doc.get("pipelineStage", "new"),
        latestGenerationRunId=doc.get("latestGenerationRunId"),
        pipelineMode=doc.get("pipelineMode", "auto"),
        pipelineStatusDetail=doc.get("pipelineStatusDetail"),
        industry=doc.get("industry"),
        notes=doc.get("notes"),
        generationTypes=doc.get("generationTypes", ["nextjs"]),
        missingFields=list(doc.get("missingFields", [])),
        version=int(doc.get("version", 1)),
        latestJob=latest_job,
        jobs=[_job_doc_to_summary(job) for job in (jobs or [])],
        pipelineEvents=pipeline_events,
        redesignSlug=doc.get("redesignSlug"),
        clientShareSiteIds=list((doc.get("clientShare") or {}).get("selectedSiteIds", [])),
        createdAt=_utc(doc["createdAt"]) or _now(),
        updatedAt=_utc(doc["updatedAt"]) or _now(),
        archivedAt=_serialize_datetime(doc.get("archivedAt")),
    )


def _lead_doc_to_list_item(
    doc: dict[str, Any], latest_job: dict[str, Any] | None = None
) -> LeadListItem:
    return LeadListItem(
        id=str(doc["id"]),
        user_id=str(doc.get("user_id", "")),
        sourceType=doc["sourceType"],
        companyName=doc.get("companyName"),
        contactName=doc.get("contactName"),
        websiteUrl=doc["websiteUrl"],
        normalizedDomain=doc["normalizedDomain"],
        status=doc["status"],
        pipelineStage=doc.get("pipelineStage", "new"),
        latestGenerationRunId=doc.get("latestGenerationRunId"),
        pipelineMode=doc.get("pipelineMode", "auto"),
        pipelineStatusDetail=doc.get("pipelineStatusDetail"),
        industry=doc.get("industry"),
        notes=doc.get("notes"),
        missingFields=list(doc.get("missingFields", [])),
        version=int(doc.get("version", 1)),
        latestJob=_job_doc_to_summary(latest_job) if latest_job else None,
        redesignSlug=doc.get("redesignSlug"),
        clientShareSiteIds=list((doc.get("clientShare") or {}).get("selectedSiteIds", [])),
        createdAt=_utc(doc["createdAt"]) or _now(),
        updatedAt=_utc(doc["updatedAt"]) or _now(),
    )


def _job_doc_to_summary(doc: dict[str, Any]) -> JobSummary:
    return JobSummary(
        id=str(doc["id"]),
        jobType=doc["jobType"],
        status=doc["status"],
        progress=int(doc.get("progress", 0)),
        step=doc.get("step", ""),
        errorMessage=doc.get("errorMessage"),
        retryCount=int(doc.get("retryCount", 0)),
        retryOfJobId=doc.get("retryOfJobId"),
        startedAt=_serialize_datetime(doc.get("startedAt")),
        finishedAt=_serialize_datetime(doc.get("finishedAt")),
        createdAt=_utc(doc["createdAt"]) or _now(),
        updatedAt=_utc(doc["updatedAt"]) or _now(),
    )


def _build_pipeline_event(
    *,
    event_type: PipelineEventType,
    status: PipelineEventStatus,
    message: str,
    detail: str | None = None,
    job_id: str | None = None,
    variant_type: str | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a pipeline event dictionary for storage."""
    return {
        "id": uuid4().hex[:12],
        "eventType": event_type,
        "status": status,
        "message": message,
        "detail": detail,
        "jobId": job_id,
        "variantType": variant_type,
        "durationMs": duration_ms,
        "metadata": metadata or {},
        "timestamp": _now(),
    }


def _pipeline_event_to_model(doc: dict[str, Any]) -> PipelineEvent:
    """Convert a pipeline event dict to a PipelineEvent model."""
    return PipelineEvent(
        id=str(doc.get("id", "")),
        eventType=doc["eventType"],
        status=doc["status"],
        message=doc["message"],
        detail=doc.get("detail"),
        jobId=doc.get("jobId"),
        variantType=doc.get("variantType"),
        durationMs=doc.get("durationMs"),
        metadata=dict(doc.get("metadata", {})),
        timestamp=_utc(doc["timestamp"]) or _now(),
    )


def _generate_redesign_slug(company_name: str | None) -> str:
    """Generate a short unique slug for the public redesign page."""
    suffix = uuid4().hex[:4]
    if not company_name:
        return f"site-{uuid4().hex[:6]}"
    # Lowercase, keep only alphanumeric chars and hyphens, replace spaces with hyphens
    slug = company_name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug.strip())
    slug = re.sub(r"-+", "-", slug).strip("-")
    slug = slug[:8].rstrip("-")
    if not slug:
        return f"site-{uuid4().hex[:6]}"
    return f"{slug}-{suffix}"


def _build_lead_doc(
    *,
    source_type: str,
    source_ref: str | None,
    company_name: str | None,
    contact_name: str | None = None,
    website_url: str,
    normalized_url: str,
    normalized_domain: str,
    industry: str | None,
    notes: str | None,
    user_id: str,
    pipeline_mode: str = "auto",
) -> dict[str, Any]:
    now = _now()
    lead_id = uuid4().hex
    initial_event = _build_pipeline_event(
        event_type="lead_created",
        status="success",
        message="Lead created",
        detail=f"Source: {source_type}",
        metadata={"sourceType": source_type, "sourceRef": source_ref},
    )
    lead = {
        "id": lead_id,
        "user_id": user_id,
        "sourceType": source_type,
        "sourceRef": source_ref,
        "sourceRefs": [
            {
                "sourceType": source_type,
                "sourceRef": source_ref,
                "importedAt": now,
            }
        ],
        "companyName": company_name,
        "contactName": contact_name,
        "websiteUrl": website_url,
        "normalizedWebsiteUrl": normalized_url,
        "normalizedDomain": normalized_domain,
        "detectedWebsiteUrl": None,
        "status": "needs_review" if not company_name else "new",
        "industry": industry,
        "notes": notes,
        "missingFields": _missing_fields(
            {"companyName": company_name, "websiteUrl": website_url}
        ),
        "version": 1,
        "latestJobId": None,
        "latestExtractionId": None,
        "jobIds": [],
        "pipelineStage": "new",
        "pipelineMode": pipeline_mode,
        "pipelineStatusDetail": None,
        "pipelineEvents": [initial_event],
        "redesignSlug": _generate_redesign_slug(company_name),
        "createdAt": now,
        "updatedAt": now,
        "archivedAt": None,
    }
    return lead


def _merge_lead_doc(
    existing: dict[str, Any], incoming: dict[str, Any]
) -> dict[str, Any]:
    merged = dict(existing)
    merged["sourceRefs"] = list(existing.get("sourceRefs", [])) + list(
        incoming.get("sourceRefs", [])
    )
    merged["sourceType"] = existing.get("sourceType") or incoming.get("sourceType")
    merged["sourceRef"] = existing.get("sourceRef") or incoming.get("sourceRef")
    if not merged.get("companyName") and incoming.get("companyName"):
        merged["companyName"] = incoming["companyName"]
    if not merged.get("websiteUrl") and incoming.get("websiteUrl"):
        merged["websiteUrl"] = incoming["websiteUrl"]
    if not merged.get("industry") and incoming.get("industry"):
        merged["industry"] = incoming["industry"]
    if not merged.get("notes") and incoming.get("notes"):
        merged["notes"] = incoming["notes"]
    merged["missingFields"] = _missing_fields(merged)
    merged["status"] = (
        "needs_review" if merged["missingFields"] else (merged.get("status") or "new")
    )
    merged["version"] = int(existing.get("version", 1)) + 1
    merged["updatedAt"] = _now()
    merged["latestJobId"] = incoming.get("latestJobId", existing.get("latestJobId"))
    merged["latestExtractionId"] = incoming.get(
        "latestExtractionId", existing.get("latestExtractionId")
    )
    merged["jobIds"] = list(
        dict.fromkeys(
            list(existing.get("jobIds", [])) + list(incoming.get("jobIds", []))
        )
    )
    return merged


class LeadRepository:
    # Maximum number of pipeline events to keep per lead (to prevent unbounded growth)
    MAX_PIPELINE_EVENTS = 100

    def __init__(self) -> None:
        self._memory_lock = asyncio.Lock()
        self._memory: dict[str, dict[str, Any]] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._extractions: dict[str, list[dict[str, Any]]] = {}
        self._briefs: dict[str, list[dict[str, Any]]] = {}
        self._memory_ready = False

    async def log_pipeline_event(
        self,
        lead_id: str,
        *,
        event_type: PipelineEventType,
        status: PipelineEventStatus,
        message: str,
        detail: str | None = None,
        job_id: str | None = None,
        variant_type: str | None = None,
        duration_ms: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a pipeline event to a lead's activity history."""
        event = _build_pipeline_event(
            event_type=event_type,
            status=status,
            message=message,
            detail=detail,
            job_id=job_id,
            variant_type=variant_type,
            duration_ms=duration_ms,
            metadata=metadata,
        )

        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is not None:
                    events = doc.setdefault("pipelineEvents", [])
                    events.append(event)
                    # Trim to max events (keep most recent)
                    if len(events) > self.MAX_PIPELINE_EVENTS:
                        doc["pipelineEvents"] = events[-self.MAX_PIPELINE_EVENTS :]
                    doc["updatedAt"] = _now()
        else:
            await database["leads"].update_one(
                {"id": lead_id},
                {
                    "$push": {
                        "pipelineEvents": {
                            "$each": [event],
                            "$slice": -self.MAX_PIPELINE_EVENTS,
                        }
                    },
                    "$set": {"updatedAt": _now()},
                },
            )

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None:
            return
        if self._memory_ready:
            return
        self._memory_ready = True
        await database["leads"].create_index("normalizedDomain")
        await database["leads"].create_index("normalizedWebsiteUrl")
        await database["jobs"].create_index("leadId")
        await database["jobs"].create_index("status")
        await database["site_extractions"].create_index("leadId")
        await database["site_extractions"].create_index(
            [("leadId", 1), ("version", -1)]
        )
        await database["site_briefs"].create_index("leadId")
        await database["site_briefs"].create_index([("leadId", 1), ("version", -1)])

    async def create_lead(
        self, request: LeadUpsertRequest, user_id: str
    ) -> LeadActionResponse:
        normalized_url, normalized_domain = _normalize_input_url(request.websiteUrl)
        pipeline_mode = request.pipelineMode or "auto"
        incoming = _build_lead_doc(
            source_type="manual",
            source_ref=None,
            company_name=request.companyName.strip() if request.companyName else None,
            contact_name=request.contactName.strip() if request.contactName else None,
            website_url=normalized_url,
            normalized_url=normalized_url,
            normalized_domain=normalized_domain,
            industry=request.industry.strip() if request.industry else None,
            notes=request.notes.strip() if request.notes else None,
            user_id=user_id,
        )
        incoming["pipelineMode"] = pipeline_mode
        incoming["pipelineStage"] = "new"
        incoming["generationTypes"] = request.generationTypes

        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                existing = self._find_duplicate_memory(normalized_domain)
                if existing is not None:
                    merged = _merge_lead_doc(existing, incoming)
                    merged["pipelineMode"] = pipeline_mode
                    self._memory[existing["id"]] = merged
                    lead = _lead_doc_to_detail(merged)
                    response = LeadActionResponse(
                        lead=lead,
                        created=False,
                        merged=True,
                        jobId=None,
                        message="Lead merged into existing record.",
                    )
                else:
                    self._memory[incoming["id"]] = incoming
                    response = LeadActionResponse(
                        lead=_lead_doc_to_detail(incoming),
                        created=True,
                        merged=False,
                        jobId=None,
                        message="Lead created.",
                    )
            await self._record_manual_lead_event(response, incoming["sourceType"])
            # Auto-start extraction for new (non-merged) leads
            if response.created:
                asyncio.create_task(
                    self._auto_start_extraction(response.lead.id),
                    name=f"auto_extract:{response.lead.id}",
                )
            return response

        existing = await database["leads"].find_one(
            {
                "normalizedDomain": normalized_domain,
                "status": {"$ne": "archived"},
            }
        )
        if existing:
            merged = _merge_lead_doc(existing, incoming)
            merged["pipelineMode"] = pipeline_mode
            await database["leads"].replace_one({"id": existing["id"]}, merged)
            response = LeadActionResponse(
                lead=_lead_doc_to_detail(merged),
                created=False,
                merged=True,
                jobId=None,
                message="Lead merged into existing record.",
            )
            await self._record_manual_lead_event(response, incoming["sourceType"])
            return response

        await database["leads"].insert_one(incoming)
        response = LeadActionResponse(
            lead=_lead_doc_to_detail(incoming),
            created=True,
            merged=False,
            jobId=None,
            message="Lead created.",
        )
        await self._record_manual_lead_event(response, incoming["sourceType"])
        # Auto-start extraction immediately
        asyncio.create_task(
            self._auto_start_extraction(response.lead.id),
            name=f"auto_extract:{response.lead.id}",
        )
        return response

    async def _auto_start_extraction(self, lead_id: str) -> None:
        """Start extraction automatically after lead creation."""
        try:
            await self._set_pipeline_stage(lead_id, "extracting")
            await self.log_pipeline_event(
                lead_id,
                event_type="extraction_started",
                status="info",
                message="Extraction started",
                detail="Crawling website for content and brand assets",
            )
            await self.start_extraction(lead_id, refresh=False)
        except Exception as exc:
            import traceback

            logging.getLogger("lenquant.pipeline").exception(
                "Auto-extraction failed for lead %s", lead_id
            )
            # Capture full error details
            error_type = type(exc).__name__
            error_msg = str(exc)
            tb_lines = traceback.format_exc().split("\n")[-5:]  # Last 5 lines
            tb_summary = "\n".join(tb_lines).strip()

            await self.log_pipeline_event(
                lead_id,
                event_type="extraction_failed",
                status="error",
                message=f"Extraction failed: {error_type}",
                detail=f"{error_msg}\n\nTraceback:\n{tb_summary}",
                metadata={"errorType": error_type, "errorMessage": error_msg},
            )
            await self._set_pipeline_stage(
                lead_id,
                "needs_attention",
                detail="Extraction could not be started automatically.",
            )

    async def _set_pipeline_stage(
        self,
        lead_id: str,
        stage: str,
        *,
        detail: str | None = None,
    ) -> None:
        """Persist pipelineStage (and optional statusDetail) for a lead."""
        now = _now()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is not None:
                    doc["pipelineStage"] = stage
                    doc["pipelineStatusDetail"] = detail
                    doc["updatedAt"] = now
        else:
            await database["leads"].update_one(
                {"id": lead_id},
                {
                    "$set": {
                        "pipelineStage": stage,
                        "pipelineStatusDetail": detail,
                        "updatedAt": now,
                    }
                },
            )

    async def _get_pipeline_mode(self, lead_id: str) -> str:
        """Return the pipelineMode for a lead (defaults to 'auto')."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                return doc.get("pipelineMode", "auto") if doc else "auto"
        doc = await database["leads"].find_one({"id": lead_id}, {"pipelineMode": 1})
        return (doc or {}).get("pipelineMode", "auto") if doc else "auto"

    async def advance_pipeline_after_extraction(self, lead_id: str) -> None:
        """Called after extraction completes — advance to brief generation if auto mode."""
        mode = await self._get_pipeline_mode(lead_id)
        extraction = await self.get_extraction(lead_id)
        if extraction is None:
            await self.log_pipeline_event(
                lead_id,
                event_type="extraction_failed",
                status="error",
                message="Extraction produced no data",
                detail="No extraction snapshot was created",
            )
            await self._set_pipeline_stage(
                lead_id, "needs_attention", detail="Extraction produced no snapshot."
            )
            return

        if extraction.crawlStatus == "failed":
            await self.log_pipeline_event(
                lead_id,
                event_type="extraction_failed",
                status="error",
                message="Extraction failed",
                detail=extraction.errors[0] if extraction.errors else "Unknown error",
            )
            await self._set_pipeline_stage(
                lead_id, "needs_attention", detail="Extraction failed."
            )
            return

        confidence = extraction.confidenceScore or 0
        pages_crawled = extraction.pagesCrawled or 0

        if confidence < 30:
            await self.log_pipeline_event(
                lead_id,
                event_type="extraction_completed",
                status="warning",
                message="Extraction completed with low confidence",
                detail=f"Confidence: {confidence}%, Pages: {pages_crawled}",
                metadata={"confidence": confidence, "pagesCrawled": pages_crawled},
            )
            await self._set_pipeline_stage(
                lead_id,
                "needs_attention",
                detail=f"Low extraction confidence ({confidence}%). Review the crawl before continuing.",
            )
            return

        await self.log_pipeline_event(
            lead_id,
            event_type="extraction_completed",
            status="success",
            message="Extraction completed",
            detail=f"Crawled {pages_crawled} pages with {confidence}% confidence",
            metadata={"confidence": confidence, "pagesCrawled": pages_crawled},
        )
        await self._set_pipeline_stage(lead_id, "extracted")

        if mode == "auto":
            # Auto mode: immediately generate master brief
            await self.log_pipeline_event(
                lead_id,
                event_type="brief_generation_started",
                status="info",
                message="Brief generation started",
                detail="Creating AI-powered master brief from extraction",
            )
            await self._set_pipeline_stage(lead_id, "briefing")
            try:
                # Use NEW AI-powered master brief (not old deterministic brief)
                master_brief = await self.create_master_brief(lead_id)
                if master_brief is None:
                    await self.log_pipeline_event(
                        lead_id,
                        event_type="pipeline_error",
                        status="error",
                        message="Brief generation returned no result",
                    )
                    await self._set_pipeline_stage(
                        lead_id,
                        "needs_attention",
                        detail="Master brief generation returned no result.",
                    )
                    return

                await self.log_pipeline_event(
                    lead_id,
                    event_type="brief_generated",
                    status="success",
                    message="Brief generated",
                    detail=f"Confidence: {master_brief.confidenceScore}%",
                    metadata={"briefVersion": master_brief.version},
                )

                # Auto-approve the master brief.
                # approve_master_brief already calls advance_pipeline_after_brief internally.
                await self.approve_master_brief(
                    lead_id=lead_id,
                    approved_by="auto",
                    notes="Auto-approved in pipeline",
                )

            except Exception as exc:
                import traceback

                logging.getLogger("lenquant.pipeline").exception(
                    "Auto master brief generation failed for lead %s", lead_id
                )
                # Capture full error details
                error_type = type(exc).__name__
                error_msg = str(exc)
                tb_lines = traceback.format_exc().split("\n")[-5:]
                tb_summary = "\n".join(tb_lines).strip()

                await self.log_pipeline_event(
                    lead_id,
                    event_type="pipeline_error",
                    status="error",
                    message=f"Brief generation failed: {error_type}",
                    detail=f"{error_msg}\n\nTraceback:\n{tb_summary}",
                    metadata={"errorType": error_type, "errorMessage": error_msg},
                )
                await self._set_pipeline_stage(
                    lead_id, "needs_attention", detail="Master brief generation failed."
                )
        else:
            # Manual mode: pause at extracted — operator approves brief
            await self.log_pipeline_event(
                lead_id,
                event_type="pipeline_paused",
                status="info",
                message="Waiting for brief approval",
                detail="Manual mode: review and approve brief to continue",
            )
            await self._set_pipeline_stage(lead_id, "brief_ready")

    async def advance_pipeline_after_brief(self, lead_id: str) -> None:
        """Called after brief is approved — queue site generation."""
        await self._set_pipeline_stage(lead_id, "generating")
        try:
            lead = await self.get_lead(lead_id)
            generation_types = lead.generationTypes if lead else ["nextjs"]
            has_html_variants = any(
                t in generation_types for t in ["html_v1", "html_v2", "html_v3"]
            )

            await self.log_pipeline_event(
                lead_id,
                event_type="site_generation_started",
                status="info",
                message="Site generation started",
                detail=f"Generating {len(generation_types)} variant(s): {', '.join(generation_types)}",
                metadata={
                    "variantCount": len(generation_types),
                    "variants": generation_types,
                },
            )

            if len(generation_types) > 1 or has_html_variants:
                from app.core.tasks import run_multi_variant_generation_task

                job = await self._create_job(
                    lead_ids=[lead_id],
                    job_type="site_generate",
                    status="queued",
                    progress=0,
                    step=f"Queued: generating {len(generation_types)} variants",
                    metadata={"generationTypes": generation_types},
                )
                run_multi_variant_generation_task.delay(  # type: ignore[attr-defined]
                    lead_id=lead_id,
                    job_id=job.id,
                    generation_types=generation_types,
                )
            else:
                from app.core.sites import site_repository

                job = await site_repository.queue_generation_job(lead_id)
                if job is None:
                    await self.log_pipeline_event(
                        lead_id,
                        event_type="site_generation_failed",
                        status="error",
                        message="Site generation could not be queued",
                    )
                    await self._set_pipeline_stage(
                        lead_id,
                        "needs_attention",
                        detail="Site generation could not be queued.",
                    )
        except Exception as exc:
            import traceback

            logging.getLogger("lenquant.pipeline").exception(
                "Auto site generation queue failed for lead %s", lead_id
            )
            # Capture full error details
            error_type = type(exc).__name__
            error_msg = str(exc)
            tb_lines = traceback.format_exc().split("\n")[-5:]
            tb_summary = "\n".join(tb_lines).strip()

            await self.log_pipeline_event(
                lead_id,
                event_type="site_generation_failed",
                status="error",
                message=f"Site generation failed: {error_type}",
                detail=f"{error_msg}\n\nTraceback:\n{tb_summary}",
                metadata={"errorType": error_type, "errorMessage": error_msg},
            )
            await self._set_pipeline_stage(
                lead_id, "needs_attention", detail="Site generation failed to start."
            )

    async def advance_pipeline_after_generation(
        self, lead_id: str, quality_score: int
    ) -> None:
        """Called after site generation completes — QA check and advance."""
        await self.log_pipeline_event(
            lead_id,
            event_type="site_generation_completed",
            status="success",
            message="Site generation completed",
            detail=f"Quality score: {quality_score}/100",
            metadata={"qualityScore": quality_score},
        )

        await self.log_pipeline_event(
            lead_id,
            event_type="qa_started",
            status="info",
            message="QA review started",
            detail=f"Evaluating site quality (score: {quality_score})",
        )
        await self._set_pipeline_stage(lead_id, "qa")
        mode = await self._get_pipeline_mode(lead_id)
        if mode == "auto":
            threshold = 75
            if quality_score >= threshold:
                await self.log_pipeline_event(
                    lead_id,
                    event_type="qa_passed",
                    status="success",
                    message="QA passed",
                    detail=f"Score {quality_score}/100 meets threshold of {threshold}",
                    metadata={"qualityScore": quality_score, "threshold": threshold},
                )
                await self._set_pipeline_stage(
                    lead_id,
                    "ready",
                    detail=f"QA passed with score {quality_score}/100.",
                )
            else:
                await self.log_pipeline_event(
                    lead_id,
                    event_type="qa_failed",
                    status="warning",
                    message="QA below threshold",
                    detail=f"Score {quality_score}/100 is below threshold {threshold}",
                    metadata={"qualityScore": quality_score, "threshold": threshold},
                )
                await self._set_pipeline_stage(
                    lead_id,
                    "needs_attention",
                    detail=f"QA score {quality_score}/100 is below threshold {threshold}. Review or regenerate.",
                )
        else:
            # Manual mode: stays in QA — operator reviews in Review queue
            await self.log_pipeline_event(
                lead_id,
                event_type="pipeline_paused",
                status="info",
                message="Waiting for QA review",
                detail="Manual mode: review site quality to continue",
            )

    def _find_duplicate_memory(self, normalized_domain: str) -> dict[str, Any] | None:
        for lead in self._memory.values():
            if (
                lead.get("normalizedDomain") == normalized_domain
                and lead.get("status") != "archived"
            ):
                return lead
        return None

    async def import_csv(
        self,
        *,
        file_name: str | None,
        csv_bytes: bytes,
        user_id: str,
        pipeline_mode: str = "auto",
    ) -> LeadImportResponse:
        await self._maybe_ensure_indexes()

        # Validation 1: File size limit (10MB max)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(csv_bytes) > max_size:
            raise ValueError(
                f"csv_too_large: File size {len(csv_bytes)} bytes exceeds {max_size} bytes limit"
            )

        # Validation 2: Detect encoding and decode safely
        try:
            text = csv_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = csv_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError(
                    "csv_invalid_encoding: File must be UTF-8 or Latin-1 encoded"
                )

        # Validation 3: Check for suspicious content (potential CSV injection)
        suspicious_prefixes = ["=", "+", "-", "@", "\t", "\r"]
        if any(text.lstrip().startswith(prefix) for prefix in suspicious_prefixes):
            raise ValueError(
                "csv_suspicious_content: CSV file contains potentially malicious content"
            )

        # Validation 4: Parse CSV with size limits
        try:
            reader = csv.DictReader(io.StringIO(text))
        except csv.Error as exc:
            raise ValueError(f"csv_parse_error: {str(exc)}")

        # Validation 5: Row count limit (1000 rows max)
        max_rows = 1000
        rows = []
        for idx, row in enumerate(reader):
            if idx >= max_rows:
                raise ValueError(f"csv_too_many_rows: Maximum {max_rows} rows allowed")
            # Only include rows with at least one non-empty value
            if any((value or "").strip() for value in row.values()):
                rows.append(row)

        if not rows:
            raise ValueError("csv_empty")

        job = await self._create_job(
            lead_ids=[],
            job_type="lead_import",
            status="running",
            progress=0,
            step="Starting CSV import",
            metadata={"fileName": file_name, "rowCount": len(rows)},
        )
        items: list[ImportRowResult] = []
        created_count = 0
        merged_count = 0
        failed_count = 0
        lead_ids: list[str] = []

        for index, row in enumerate(rows, start=1):
            try:
                lead, created, merged, message = await self._import_row(
                    row,
                    source_ref=f"{file_name or 'csv'}:row:{index}",
                    user_id=user_id,
                    pipeline_mode=pipeline_mode,
                )
                if lead:
                    lead_ids.append(lead["id"])
                if created:
                    created_count += 1
                elif merged:
                    merged_count += 1
                items.append(
                    ImportRowResult(
                        rowNumber=index,
                        status="created"
                        if created
                        else ("merged" if merged else "failed"),
                        leadId=lead["id"] if lead else None,
                        companyName=lead.get("companyName")
                        if lead
                        else row.get("companyName"),
                        websiteUrl=lead.get("websiteUrl")
                        if lead
                        else row.get("websiteUrl") or row.get("url"),
                        normalizedDomain=lead.get("normalizedDomain") if lead else None,
                        message=message,
                        missingFields=list(lead.get("missingFields", []))
                        if lead
                        else [],
                    )
                )
                await self._update_job(
                    job.id,
                    progress=min(95, int(index / max(len(rows), 1) * 90)),
                    step=f"Processed row {index} of {len(rows)}",
                    lead_ids=lead_ids,
                )
            except Exception as exc:
                failed_count += 1
                items.append(
                    ImportRowResult(
                        rowNumber=index,
                        status="failed",
                        message=str(exc),
                        missingFields=[],
                    )
                )

        await self._update_job(
            job.id,
            status="completed",
            progress=100,
            step="CSV import complete",
            finished=True,
            lead_ids=list(dict.fromkeys(lead_ids)),
        )
        completed_job = await self.get_job(job.id)
        if completed_job is None:
            raise RuntimeError("import_job_missing")
        response = LeadImportResponse(
            job=completed_job,
            items=items,
            totalRows=len(rows),
            createdCount=created_count,
            mergedCount=merged_count,
            failedCount=failed_count,
            leadIds=list(dict.fromkeys(lead_ids)),
        )
        await analytics_repository.record_admin_event(
            event_type="lead_imported",
            event_name="CSV import completed",
            metadata={
                "fileName": file_name,
                "created": created_count,
                "merged": merged_count,
                "failed": failed_count,
            },
        )
        return response

    async def _import_row(
        self,
        row: dict[str, str],
        *,
        source_ref: str | None,
        user_id: str,
        pipeline_mode: str = "auto",
    ) -> tuple[dict[str, Any] | None, bool, bool, str]:
        company_name = self._read_column(row, ["companyName", "company", "name"])
        website_value = self._read_column(
            row, ["websiteUrl", "website", "url", "domain"]
        )
        notes = self._read_column(row, ["notes", "note"])
        industry = self._read_column(row, ["industry", "sector"])

        if not website_value:
            raise ValueError("website_url_required")

        normalized_url, normalized_domain = _normalize_input_url(website_value)
        incoming = _build_lead_doc(
            source_type="csv",
            source_ref=source_ref,
            company_name=company_name.strip() if company_name else None,
            website_url=normalized_url,
            normalized_url=normalized_url,
            normalized_domain=normalized_domain,
            industry=industry.strip() if industry else None,
            notes=notes.strip() if notes else None,
            user_id=user_id,
            pipeline_mode=pipeline_mode,
        )

        database = get_database()
        if database is None:
            async with self._memory_lock:
                existing = self._find_duplicate_memory(normalized_domain)
                if existing is not None:
                    merged = _merge_lead_doc(existing, incoming)
                    self._memory[existing["id"]] = merged
                    response = (merged, False, True, "Merged into existing lead.")
                else:
                    self._memory[incoming["id"]] = incoming
                    response = (incoming, True, False, "Lead created.")
            await self._record_lead_import_event(response, source_ref)
            return response

        existing = await database["leads"].find_one(
            {
                "normalizedDomain": normalized_domain,
                "status": {"$ne": "archived"},
            }
        )
        if existing:
            merged = _merge_lead_doc(existing, incoming)
            await database["leads"].replace_one({"id": existing["id"]}, merged)
            response = (merged, False, True, "Merged into existing lead.")
            await self._record_lead_import_event(response, source_ref)
            return response

        await database["leads"].insert_one(incoming)
        response = (incoming, True, False, "Lead created.")
        await self._record_lead_import_event(response, source_ref)
        return response

    async def _record_manual_lead_event(
        self, response: LeadActionResponse, source_type: str
    ) -> None:
        if response.lead is None:
            return
        if response.merged:
            event_type = "lead_merged"
            event_name = "Manual lead merged into existing record"
        else:
            event_type = "lead_created"
            event_name = "Lead created via manual intake"
        await analytics_repository.record_admin_event(
            event_type=event_type,
            event_name=event_name,
            lead_id=response.lead.id,
            metadata={"sourceType": source_type},
        )

    async def _record_brief_event(
        self, lead_id: str, *, event_type: str, event_name: str, version: int
    ) -> None:
        from typing import cast
        from ..schemas.analytics import AnalyticsEventType

        await analytics_repository.record_admin_event(
            event_type=cast(AnalyticsEventType, event_type),
            event_name=event_name,
            lead_id=lead_id,
            metadata={"briefVersion": version},
        )

    async def _record_lead_import_event(
        self,
        result: tuple[dict[str, Any] | None, bool, bool, str],
        source_ref: str | None,
    ) -> None:
        lead_doc, created, merged, _message = result
        if lead_doc is None:
            return
        event_type = "lead_created" if created else "lead_merged"
        event_name = "CSV lead created" if created else "CSV lead merged"
        await analytics_repository.record_admin_event(
            event_type=event_type,
            event_name=event_name,
            lead_id=str(lead_doc["id"]),
            metadata={"sourceRef": source_ref},
        )

    def _read_column(
        self, row: dict[str, str], candidates: Iterable[str]
    ) -> Optional[str]:
        normalized_row = _normalized_row(row)
        for key in candidates:
            value = normalized_row.get(key.strip().lower())
            if value is not None:
                value = value.strip()
                if value:
                    return value
        return None

    async def list_leads(
        self,
        q: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        limit: int = 25,
        offset: int = 0,
        user_id: str | None = None,
    ) -> LeadListResponse:
        # Validate pagination parameters
        max_limit = 100
        max_offset = 10000
        if limit < 1 or limit > max_limit:
            raise ValueError(f"limit must be between 1 and {max_limit}")
        if offset < 0 or offset > max_offset:
            raise ValueError(f"offset must be between 0 and {max_offset}")

        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                items = self._list_memory_leads(
                    q=q, status=status, limit=limit, offset=offset
                )
                total = self._count_memory_leads(q=q, status=status)
                summary = self._compute_pipeline_summary_memory()
                return LeadListResponse(
                    items=items,
                    pagination={"total": total, "limit": limit, "offset": offset},
                    pipelineSummary=summary,
                )

        query: dict[str, Any] = {}
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        else:
            query["status"] = {"$ne": "archived"}
        if stage:
            query["pipelineStage"] = stage
        if q:
            pattern = {"$regex": re.escape(q), "$options": "i"}
            query["$or"] = [
                {"companyName": pattern},
                {"websiteUrl": pattern},
                {"normalizedDomain": pattern},
            ]
        cursor = (
            database["leads"]
            .find(query)
            .sort("updatedAt", -1)
            .skip(offset)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        total = await database["leads"].count_documents(query)
        items = [await self._lead_list_item_for_doc(doc, database) for doc in docs]
        summary = await self._compute_pipeline_summary_db(database, user_id=user_id)
        return LeadListResponse(
            items=items,
            pagination={"total": total, "limit": limit, "offset": offset},
            pipelineSummary=summary,
        )

    def _list_memory_leads(
        self, q: str | None, status: str | None, limit: int, offset: int
    ) -> list[LeadListItem]:
        docs = list(self._memory.values())
        if status:
            docs = [doc for doc in docs if doc.get("status") == status]
        if q:
            pattern = q.lower()
            docs = [
                doc
                for doc in docs
                if pattern in (doc.get("companyName") or "").lower()
                or pattern in (doc.get("websiteUrl") or "").lower()
                or pattern in (doc.get("normalizedDomain") or "").lower()
            ]
        docs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
        sliced = docs[offset : offset + limit]
        return [
            _lead_doc_to_list_item(doc, self._latest_job_memory(doc.get("latestJobId")))
            for doc in sliced
        ]

    def _count_memory_leads(self, q: str | None, status: str | None) -> int:
        return len(self._list_memory_leads(q=q, status=status, limit=10**6, offset=0))

    def _compute_pipeline_summary_memory(self):  # type: ignore[return]
        from app.schemas.lead import PipelineSummary

        counts = {
            "processing": 0,
            "needs_attention": 0,
            "brief_ready": 0,
            "site_generated": 0,
            "ready_to_publish": 0,
            "published": 0,
        }
        processing_stages = {"extracting", "extracted", "briefing", "generating", "qa"}
        for doc in self._memory.values():
            stage = doc.get("pipelineStage", "new")
            if doc.get("status") == "archived":
                continue
            if stage in processing_stages:
                counts["processing"] += 1
            elif stage == "needs_attention":
                counts["needs_attention"] += 1
            elif stage == "brief_ready":
                counts["brief_ready"] += 1
            elif stage == "qa":
                counts["site_generated"] += 1
            elif stage == "ready":
                counts["ready_to_publish"] += 1
            elif stage == "published":
                counts["published"] += 1
        return PipelineSummary(**counts)

    async def _compute_pipeline_summary_db(self, database, user_id: str | None = None):  # type: ignore[return]
        from app.schemas.lead import PipelineSummary

        pipeline_stages = [
            "new",
            "extracting",
            "extracted",
            "briefing",
            "brief_ready",
            "generating",
            "qa",
            "ready",
            "published",
            "needs_attention",
        ]
        counts = {
            "processing": 0,
            "needs_attention": 0,
            "brief_ready": 0,
            "site_generated": 0,
            "ready_to_publish": 0,
            "published": 0,
        }
        try:
            match_filter: dict[str, Any] = {"status": {"$ne": "archived"}}
            if user_id:
                match_filter["user_id"] = user_id
            agg = (
                await database["leads"]
                .aggregate(
                    [
                        {"$match": match_filter},
                        {"$group": {"_id": "$pipelineStage", "count": {"$sum": 1}}},
                    ]
                )
                .to_list(length=len(pipeline_stages) + 5)
            )
            processing_stages = {"extracting", "extracted", "briefing", "generating"}
            for entry in agg:
                stage = entry.get("_id") or "new"
                count = entry.get("count", 0)
                if stage in processing_stages:
                    counts["processing"] += count
                elif stage == "needs_attention":
                    counts["needs_attention"] += count
                elif stage == "brief_ready":
                    counts["brief_ready"] += count
                elif stage == "qa":
                    counts["site_generated"] += count
                elif stage == "ready":
                    counts["ready_to_publish"] += count
                elif stage == "published":
                    counts["published"] += count
        except Exception:
            pass
        return PipelineSummary(**counts)

    async def _lead_list_item_for_doc(
        self, doc: dict[str, Any], database
    ) -> LeadListItem:
        latest_job = None
        latest_job_id = doc.get("latestJobId")
        if latest_job_id:
            latest_job = await database["jobs"].find_one({"id": latest_job_id})
        return _lead_doc_to_list_item(doc, latest_job)

    async def get_lead(
        self, lead_id: str, user_id: str | None = None
    ) -> LeadDetail | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is None:
                    return None
                jobs = self._jobs_for_lead_memory(lead_id)
                return _lead_doc_to_detail(doc, jobs)

        query: dict[str, Any] = {"id": lead_id}
        if user_id:
            query["user_id"] = user_id
        doc = await database["leads"].find_one(query)
        if doc is None:
            return None
        jobs_cursor = (
            database["jobs"].find({"leadIds": lead_id}).sort("updatedAt", -1).limit(10)
        )
        jobs = await jobs_cursor.to_list(length=10)
        if doc.get("latestJobId"):
            latest_job = await database["jobs"].find_one({"id": doc["latestJobId"]})
            if latest_job and all(job["id"] != latest_job["id"] for job in jobs):
                jobs = [latest_job] + jobs
        return _lead_doc_to_detail(doc, jobs)

    async def get_lead_ids_for_user(self, user_id: str) -> list[str]:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return [
                    doc["id"]
                    for doc in self._memory.values()
                    if doc.get("user_id") == user_id
                ]
        cursor = database["leads"].find({"user_id": user_id}, {"id": 1})
        docs = await cursor.to_list(length=None)
        return [str(doc["id"]) for doc in docs if doc.get("id")]

    def _jobs_for_lead_memory(self, lead_id: str) -> list[dict[str, Any]]:
        jobs = [job for job in self._jobs.values() if lead_id in job.get("leadIds", [])]
        jobs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
        return jobs[:10]

    def _latest_job_memory(self, job_id: str | None) -> dict[str, Any] | None:
        if not job_id:
            return None
        return self._jobs.get(job_id)

    async def update_lead(
        self, lead_id: str, patch: LeadPatchRequest, user_id: str | None = None
    ) -> LeadDetail | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is None:
                    return None
                updated = self._apply_patch(doc, patch)
                self._memory[lead_id] = updated
            return _lead_doc_to_detail(updated, self._jobs_for_lead_memory(lead_id))

        query: dict[str, Any] = {"id": lead_id}
        if user_id:
            query["user_id"] = user_id
        doc = await database["leads"].find_one(query)
        if doc is None:
            return None

        expected_version = getattr(patch, "expectedVersion", None)
        if expected_version is not None:
            current_version = int(doc.get("version", 1))
            if current_version != expected_version:
                raise ValueError(
                    f"Concurrent modification detected. Expected version {expected_version}, found {current_version}"
                )

        updated = self._apply_patch(doc, patch)
        result = await database["leads"].replace_one(
            {"id": lead_id, "version": doc.get("version", 1)}, updated
        )
        if result.matched_count == 0:
            raise ValueError("Concurrent modification detected. Please refresh and try again.")
        return await self.get_lead(lead_id, user_id=user_id)

    async def update_generation_stage_if_latest(
        self, lead_id: str, generation_run_id: str, stage: str
    ) -> bool:
        """Update pipeline stage only while this run is still the lead's latest run."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if not doc or doc.get("latestGenerationRunId") != generation_run_id:
                    return False
                doc["pipelineStage"] = stage
                doc["version"] = int(doc.get("version", 1)) + 1
                doc["updatedAt"] = _now()
                return True
        result = await database["leads"].update_one(
            {"id": lead_id, "latestGenerationRunId": generation_run_id},
            {"$set": {"pipelineStage": stage, "updatedAt": _now()}, "$inc": {"version": 1}},
        )
        return result.modified_count == 1

    async def save_client_share(
        self, lead_id: str, site_ids: list[str], user_id: str,
        booking_url: str | None = None,
    ) -> dict[str, Any] | None:
        """Persist the operator's ordered optional client-share selection."""
        from app.core.sites import site_repository

        unique_ids = list(dict.fromkeys(site_ids))
        if len(unique_ids) > 0 and any(not isinstance(site_id, str) or not site_id.strip() for site_id in unique_ids):
            raise ValueError("Selected website IDs must be non-empty strings.")
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None
        sites = await site_repository.list_sites_by_lead(lead_id, user_id=user_id)
        by_id = {site.id: site for site in sites}
        selected = [by_id.get(site_id) for site_id in unique_ids]
        if any(site is None for site in selected):
            raise ValueError("Every selected website must belong to this lead.")
        if any(
            (
                site.compilationStatus not in {"success", "completed"}
                and not site.staticHtml
            )
            or not (site.previewUrl or site.previewSlug)
            or site.readinessStatus == "blocked"
            for site in selected
            if site is not None
        ):
            raise ValueError("Only available, non-blocked websites with a preview can be shared.")

        now = _now()
        share = {
            "id": (lead.redesignSlug or uuid4().hex),
            "leadId": lead_id,
            "slug": lead.redesignSlug or uuid4().hex,
            "selectedSiteIds": unique_ids,
            "bookingUrl": booking_url or "https://calendly.com/lenquant/sites",
            "createdAt": now,
            "updatedAt": now,
            "isActive": True,
        }
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is None:
                    return None
                doc["clientShare"] = share
                doc["updatedAt"] = now
        else:
            await database["leads"].update_one(
                {"id": lead_id, "user_id": user_id},
                {"$set": {"clientShare": share, "updatedAt": now}},
            )
        return {
            "id": share["id"],
            "leadId": lead_id,
            "slug": share["slug"],
            "siteIds": unique_ids,
            "url": f"{os.getenv('FRONTEND_PUBLIC_URL', 'https://sites.lenquant.com').rstrip('/')}/redesign/{share['slug']}",
            "bookingUrl": share["bookingUrl"],
            "updatedAt": now,
        }

    async def get_client_share(
        self, lead_id: str, user_id: str
    ) -> dict[str, Any] | None:
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None
        database = get_database()
        if database is None:
            async with self._memory_lock:
                share = self._memory.get(lead_id, {}).get("clientShare")
        else:
            doc = await database["leads"].find_one({"id": lead_id, "user_id": user_id})
            share = doc.get("clientShare") if doc else None
        if not share:
            return None
        return {
            "id": share.get("id", lead.redesignSlug),
            "leadId": lead_id,
            "slug": share.get("slug", lead.redesignSlug),
            "siteIds": list(share.get("selectedSiteIds", [])),
            "url": f"{os.getenv('FRONTEND_PUBLIC_URL', 'https://sites.lenquant.com').rstrip('/')}/redesign/{share.get('slug', lead.redesignSlug)}",
            "bookingUrl": share.get("bookingUrl") or "https://calendly.com/lenquant/sites",
            "updatedAt": _utc(share.get("updatedAt")) or _now(),
        }

    def _apply_patch(
        self, doc: dict[str, Any], patch: LeadPatchRequest
    ) -> dict[str, Any]:
        updated = dict(doc)
        if patch.companyName is not None:
            updated["companyName"] = patch.companyName.strip() or None
        if patch.contactName is not None:
            updated["contactName"] = patch.contactName.strip() or None
        if patch.websiteUrl is not None:
            normalized_url, normalized_domain = _normalize_input_url(patch.websiteUrl)
            updated["websiteUrl"] = normalized_url
            updated["normalizedWebsiteUrl"] = normalized_url
            updated["normalizedDomain"] = normalized_domain
        if patch.industry is not None:
            updated["industry"] = patch.industry.strip() or None
        if patch.notes is not None:
            updated["notes"] = patch.notes.strip() or None
        if patch.status is not None:
            updated["status"] = patch.status
            if patch.status == "archived":
                updated["archivedAt"] = _now()
            elif updated.get("archivedAt"):
                updated["archivedAt"] = None
        if patch.pipelineMode is not None:
            updated["pipelineMode"] = patch.pipelineMode
        if patch.pipelineStage is not None:
            updated["pipelineStage"] = patch.pipelineStage
        if patch.latestGenerationRunId is not None:
            updated["latestGenerationRunId"] = patch.latestGenerationRunId
        if patch.generationTypes is not None:
            updated["generationTypes"] = patch.generationTypes
        updated["missingFields"] = _missing_fields(updated)
        if updated["status"] != "archived":
            updated["status"] = (
                "needs_review"
                if updated["missingFields"]
                else updated.get("status", "new")
            )
        updated["version"] = int(updated.get("version", 1)) + 1
        updated["updatedAt"] = _now()
        return updated

    async def archive_lead(
        self, lead_id: str, user_id: str | None = None
    ) -> LeadDetail | None:
        return await self.update_lead(
            lead_id, LeadPatchRequest(status="archived"), user_id=user_id
        )

    async def create_job(
        self,
        *,
        lead_ids: list[str],
        job_type: str,
        status: str,
        progress: int,
        step: str,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
        job_id: str | None = None,
    ) -> JobSummary:
        await self._maybe_ensure_indexes()
        job = await self._create_job(
            lead_ids=lead_ids,
            job_type=job_type,
            status=status,
            progress=progress,
            step=step,
            metadata=metadata,
            error_message=error_message,
            job_id=job_id,
        )
        return job

    async def _create_job(
        self,
        *,
        lead_ids: list[str],
        job_type: str,
        status: str,
        progress: int,
        step: str,
        metadata: dict[str, Any] | None = None,
        error_message: str | None = None,
        job_id: str | None = None,
    ) -> JobSummary:
        now = _now()
        doc = {
            "id": job_id or uuid4().hex,
            "leadId": lead_ids[0] if len(lead_ids) == 1 else None,
            "leadIds": lead_ids,
            "jobType": job_type,
            "status": status,
            "progress": progress,
            "step": step,
            "errorMessage": error_message,
            "startedAt": now if status in {"running", "completed", "failed"} else None,
            "finishedAt": now if status in {"completed", "failed"} else None,
            "metadata": metadata or {},
            "createdAt": now,
            "updatedAt": now,
        }
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._jobs[doc["id"]] = doc
                for lead_id in lead_ids:
                    lead = self._memory.get(lead_id)
                    if lead is not None:
                        lead["latestJobId"] = doc["id"]
                        lead["jobIds"] = list(
                            dict.fromkeys(list(lead.get("jobIds", [])) + [doc["id"]])
                        )
                        lead["updatedAt"] = now
                return _job_doc_to_summary(doc)

        await database["jobs"].insert_one(doc)
        for lead_id in lead_ids:
            await database["leads"].update_one(
                {"id": lead_id},
                {
                    "$set": {"latestJobId": doc["id"], "updatedAt": now},
                    "$addToSet": {"jobIds": doc["id"]},
                },
            )
        return _job_doc_to_summary(doc)

    async def _update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        step: str | None = None,
        finished: bool = False,
        lead_ids: list[str] | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = _now()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                job = self._jobs.get(job_id)
                if job is None:
                    return
                if status is not None:
                    job["status"] = status
                    if status == "running" and job.get("startedAt") is None:
                        job["startedAt"] = now
                if progress is not None:
                    job["progress"] = progress
                if step is not None:
                    job["step"] = step
                if error_message is not None:
                    job["errorMessage"] = error_message
                if metadata is not None:
                    job["metadata"] = metadata
                if finished:
                    job["finishedAt"] = now
                job["updatedAt"] = now
                if lead_ids is not None:
                    job["leadIds"] = lead_ids
                    job["leadId"] = lead_ids[0] if len(lead_ids) == 1 else None
                    for lead_id in lead_ids:
                        lead = self._memory.get(lead_id)
                        if lead is not None:
                            lead["latestJobId"] = job_id
                            lead["jobIds"] = list(
                                dict.fromkeys(list(lead.get("jobIds", [])) + [job_id])
                            )
                            lead["updatedAt"] = now
                return

        update: dict[str, Any] = {"updatedAt": now}
        if status is not None:
            update["status"] = status
        if progress is not None:
            update["progress"] = progress
        if step is not None:
            update["step"] = step
        if error_message is not None:
            update["errorMessage"] = error_message
        if metadata is not None:
            update["metadata"] = metadata
        if finished:
            update["finishedAt"] = now
        await database["jobs"].update_one({"id": job_id}, {"$set": update})
        if status == "running":
            # Only stamp startedAt the first time; don't overwrite if already set
            await database["jobs"].update_one(
                {"id": job_id, "startedAt": None},
                {"$set": {"startedAt": now}},
            )
        if lead_ids is not None:
            await database["jobs"].update_one(
                {"id": job_id},
                {
                    "$set": {
                        "leadIds": lead_ids,
                        "leadId": lead_ids[0] if len(lead_ids) == 1 else None,
                    }
                },
            )
            for lead_id in lead_ids:
                await database["leads"].update_one(
                    {"id": lead_id},
                    {
                        "$set": {"latestJobId": job_id, "updatedAt": now},
                        "$addToSet": {"jobIds": job_id},
                    },
                )

    async def get_job(
        self, job_id: str, user_id: str | None = None
    ) -> JobSummary | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                job = self._jobs.get(job_id)
                return _job_doc_to_summary(job) if job else None
        doc = await database["jobs"].find_one({"id": job_id})
        if doc is None:
            return None
        if user_id:
            lead_ids = list(doc.get("leadIds", []))
            if lead_id := doc.get("leadId"):
                if lead_id not in lead_ids:
                    lead_ids.append(lead_id)
            if lead_ids:
                owned_count = await database["leads"].count_documents(
                    {"id": {"$in": lead_ids}, "user_id": user_id}
                )
                if owned_count == 0:
                    return None
        return _job_doc_to_summary(doc)

    async def get_job_doc(self, job_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._jobs.get(job_id)
        return await database["jobs"].find_one({"id": job_id})

    async def retry_job(
        self, job_id: str, *, request: JobRetryRequest | None = None
    ) -> JobSummary | None:
        await self._maybe_ensure_indexes()
        source = await self.get_job_doc(job_id)
        if source is None:
            return None
        if source.get("status") not in {"failed", "completed"}:
            return _job_doc_to_summary(source)

        retry_count = int(source.get("retryCount", 0)) + 1
        metadata = dict(source.get("metadata", {}))
        if request and request.reason:
            metadata["retryReason"] = request.reason
        metadata["retryOfJobId"] = source["id"]
        metadata["retryCount"] = retry_count
        lead_ids = list(source.get("leadIds", []))
        job = await self._create_job(
            lead_ids=lead_ids,
            job_type=source.get("jobType", "lead_import"),
            status="queued",
            progress=0,
            step=source.get("step", "Queued for retry"),
            metadata=metadata,
        )
        await self._update_job(
            job.id,
            status="queued",
            progress=0,
            step="Queued for retry",
            metadata={
                **metadata,
                "retryOfJobId": source["id"],
                "retryCount": retry_count,
            },
        )
        database = get_database()
        if database is None:
            async with self._memory_lock:
                retry_doc = self._jobs[job.id]
                retry_doc["retryOfJobId"] = source["id"]
                retry_doc["retryCount"] = retry_count
                retry_doc["status"] = "queued"
                retry_doc["progress"] = 0
                retry_doc["step"] = "Queued for retry"
        else:
            await database["jobs"].update_one(
                {"id": job.id},
                {
                    "$set": {
                        "retryOfJobId": source["id"],
                        "retryCount": retry_count,
                        "status": "queued",
                        "progress": 0,
                        "step": "Queued for retry",
                    }
                },
            )

        # Actually dispatch the job to Celery so it runs (not just written to Mongo)
        job_type = source.get("jobType", "")
        if job_type in ("site_crawl", "site_refresh"):
            lead_id = lead_ids[0] if lead_ids else None
            if lead_id:
                await self._dispatch_extraction_job(
                    job_id=job.id,
                    lead_id=lead_id,
                    refresh=(job_type == "site_refresh"),
                )
        elif job_type in ("site_generate", "site_republish"):
            lead_id = lead_ids[0] if lead_ids else None
            if lead_id:
                from app.core.sites import (
                    site_repository,
                )  # avoid circular at module level

                await site_repository._dispatch_generation_job(  # type: ignore[attr-defined]
                    site_id=lead_id, job_id=job.id, request=None
                )

        if database is None:
            async with self._memory_lock:
                return _job_doc_to_summary(self._jobs[job.id])
        return await self.get_job(job.id)

    async def get_queue_health(
        self, user_id: str | None = None
    ) -> JobQueueHealthResponse:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = list(self._jobs.values())
        else:
            if user_id:
                lead_ids = await self.get_lead_ids_for_user(user_id)
                query: dict[str, Any] = (
                    {"leadId": {"$in": lead_ids}} if lead_ids else {"leadId": None}
                )
            else:
                query = {}
            cursor = database["jobs"].find(query).sort("updatedAt", -1).limit(250)
            docs = await cursor.to_list(length=250)

        total = len(docs)
        queued = sum(1 for doc in docs if doc.get("status") == "queued")
        running = sum(1 for doc in docs if doc.get("status") == "running")
        failed = sum(1 for doc in docs if doc.get("status") == "failed")
        completed = sum(1 for doc in docs if doc.get("status") == "completed")

        def _stalled(doc: dict[str, Any]) -> bool:
            status = doc.get("status")
            updated_at = _utc(doc.get("updatedAt")) or _now()
            age_seconds = (_now() - updated_at).total_seconds()
            return status == "running" and age_seconds > 1800

        stalled_docs = [doc for doc in docs if _stalled(doc)]
        failed_docs = [doc for doc in docs if doc.get("status") == "failed"]
        queued_docs = sorted(
            [doc for doc in docs if doc.get("status") == "queued"],
            key=lambda d: _utc(d.get("createdAt")) or _now(),
        )
        by_type: dict[str, int] = {}
        for doc in docs:
            by_type[doc.get("jobType", "unknown")] = (
                by_type.get(doc.get("jobType", "unknown"), 0) + 1
            )

        def _health_item(doc: dict[str, Any]) -> JobQueueHealthItem:
            created_at = _serialize_datetime(doc.get("createdAt")) or _now()
            updated_at = _serialize_datetime(doc.get("updatedAt")) or _now()
            return JobQueueHealthItem(
                id=str(doc.get("id", "")),
                jobType=str(doc.get("jobType", "unknown")),
                status=str(doc.get("status", "queued")),
                progress=int(doc.get("progress", 0)),
                step=str(doc.get("step", "")),
                errorMessage=doc.get("errorMessage"),
                leadIds=list(doc.get("leadIds", [])),
                retryCount=int(doc.get("retryCount", 0)),
                retryOfJobId=doc.get("retryOfJobId"),
                stalled=_stalled(doc),
                createdAt=created_at.isoformat(),
                updatedAt=updated_at.isoformat(),
            )

        return JobQueueHealthResponse(
            totalJobs=total,
            queuedJobs=queued,
            runningJobs=running,
            failedJobs=failed,
            completedJobs=completed,
            stalledJobs=len(stalled_docs),
            backlogJobs=queued + len(stalled_docs),
            byType=by_type,
            stalledItems=[_health_item(doc) for doc in stalled_docs[:25]],
            failedItems=[_health_item(doc) for doc in failed_docs[:25]],
            queuedItems=[_health_item(doc) for doc in queued_docs[:50]],
            updatedAt=_now().isoformat(),
        )

    async def recent_job_errors(self, limit: int = 10) -> list[dict[str, Any]]:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = [
                    doc for doc in self._jobs.values() if doc.get("status") == "failed"
                ]
                docs.sort(
                    key=lambda doc: _serialize_datetime(doc.get("updatedAt")) or _now(),
                    reverse=True,
                )
                top = docs[:limit]
        else:
            cursor = (
                database["jobs"]
                .find({"status": "failed"})
                .sort("updatedAt", -1)
                .limit(limit)
            )
            top = await cursor.to_list(length=limit)

        results: list[dict[str, Any]] = []
        for doc in top:
            updated_at = (
                _serialize_datetime(doc.get("updatedAt"))
                or _serialize_datetime(doc.get("createdAt"))
                or _now()
            )
            lead_ids = doc.get("leadIds") or (
                [] if doc.get("leadId") is None else [doc.get("leadId")]
            )
            results.append(
                {
                    "id": str(doc.get("id", "")),
                    "leadId": lead_ids[0] if lead_ids else None,
                    "jobType": str(doc.get("jobType", "unknown")),
                    "step": str(doc.get("step", "")),
                    "errorMessage": doc.get("errorMessage"),
                    "updatedAt": updated_at,
                }
            )
        return results

    async def delete_lead(
        self, lead_id: str, user_id: str | None = None
    ) -> LeadDetail | None:
        return await self.archive_lead(lead_id, user_id=user_id)

    async def search_jobs_for_lead(self, lead_id: str) -> list[JobSummary]:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return [
                    _job_doc_to_summary(job)
                    for job in self._jobs_for_lead_memory(lead_id)
                ]
        cursor = (
            database["jobs"].find({"leadIds": lead_id}).sort("updatedAt", -1).limit(10)
        )
        docs = await cursor.to_list(length=10)
        return [_job_doc_to_summary(doc) for doc in docs]

    def _latest_extraction_memory(self, lead_id: str) -> dict[str, Any] | None:
        extractions = self._extractions.get(lead_id, [])
        if not extractions:
            return None
        return max(extractions, key=lambda item: item.get("version", 0))

    async def _latest_extraction_doc(self, lead_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._latest_extraction_memory(lead_id)
        return await database["site_extractions"].find_one(
            {"leadId": lead_id}, sort=[("version", -1)]
        )

    def _extraction_doc_to_snapshot(self, doc: dict[str, Any]) -> ExtractionSnapshot:
        # Clean pageInventory meta dict to remove None values
        page_inventory = list(doc.get("pageInventory", []))
        for page in page_inventory:
            if "meta" in page and isinstance(page["meta"], dict):
                page["meta"] = {k: v for k, v in page["meta"].items() if v is not None}

        return ExtractionSnapshot(
            id=str(doc["id"]),
            leadId=str(doc["leadId"]),
            jobId=doc.get("jobId"),
            version=int(doc.get("version", 1)),
            crawlStatus=doc["crawlStatus"],
            sitemapStatus=doc["sitemapStatus"],
            pagesDiscovered=int(doc.get("pagesDiscovered", 0)),
            pagesCrawled=int(doc.get("pagesCrawled", 0)),
            canonicalWebsiteUrl=doc["canonicalWebsiteUrl"],
            detectedWebsiteUrl=doc.get("detectedWebsiteUrl"),
            summary=doc["summary"],
            pageInventory=page_inventory,
            sourceCitations=list(doc.get("sourceCitations", [])),
            brandAssetCues=list(doc.get("brandAssetCues", [])),
            assetManifest=list(doc.get("assetManifest", [])),
            sectionInventory=list(doc.get("sectionInventory", [])),
            visualCaptureSummary=dict(doc.get("visualCaptureSummary", {})),
            sitemapUrls=list(doc.get("sitemapUrls", [])),
            confidenceScore=int(doc.get("confidenceScore", 0)),
            gapItems=list(doc.get("gapItems", [])),
            errors=list(doc.get("errors", [])),
            analysis=doc.get("analysis"),
            extractedTestimonials=list(doc.get("extractedTestimonials", [])),
            extractedClientLogos=list(doc.get("extractedClientLogos", [])),
            extractedFonts=list(doc.get("extractedFonts", [])),
            extractedImages=list(doc.get("extractedImages", [])),
            createdAt=_utc(doc["createdAt"]) or _now(),
            updatedAt=_utc(doc["updatedAt"]) or _now(),
        )

    def _empty_extraction_snapshot(self, lead: LeadDetail) -> ExtractionSnapshot:
        now = lead.updatedAt
        return ExtractionSnapshot(
            id=f"pending-{lead.id}",
            leadId=lead.id,
            jobId=None,
            version=0,
            crawlStatus="idle",
            sitemapStatus="unknown",
            pagesDiscovered=0,
            pagesCrawled=0,
            canonicalWebsiteUrl=lead.websiteUrl,
            detectedWebsiteUrl=lead.detectedWebsiteUrl,
            summary=ExtractionSummary(
                companyName=lead.companyName,
                canonicalWebsiteUrl=lead.websiteUrl,
                detectedWebsiteUrl=lead.detectedWebsiteUrl,
                positioningSummary=None,
                audienceClues=[],
                serviceClues=[],
                ctaClues=[],
                toneClues=[],
            ),
            pageInventory=[],
            sourceCitations=[],
            brandAssetCues=[],
            assetManifest=[],
            sectionInventory=[],
            visualCaptureSummary={},
            sitemapUrls=[],
            confidenceScore=0,
            gapItems=["crawl_not_started"],
            errors=[],
            analysis=None,
            extractedTestimonials=[],
            extractedClientLogos=[],
            extractedFonts=[],
            extractedImages=[],
            createdAt=now,
            updatedAt=now,
        )

    async def get_extraction(
        self, lead_id: str, user_id: str | None = None
    ) -> ExtractionSnapshot | None:
        await self._maybe_ensure_indexes()
        doc = await self._latest_extraction_doc(lead_id)
        if doc is None:
            lead = await self.get_lead(lead_id, user_id=user_id)
            if lead is None:
                return None
            return self._empty_extraction_snapshot(lead)
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None
        return self._extraction_doc_to_snapshot(doc)

    async def get_extraction_version(
        self, lead_id: str, extraction_id: str, version: int
    ) -> ExtractionSnapshot | None:
        """Load the exact extraction pinned by a generation run."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = self._extractions.get(lead_id, [])
                doc = next((d for d in docs if str(d.get("id")) == extraction_id and int(d.get("version", 0)) == version), None)
        else:
            doc = await database["site_extractions"].find_one({"id": extraction_id, "leadId": lead_id, "version": version})
        return self._extraction_doc_to_snapshot(doc) if doc else None

    async def list_pages(
        self, lead_id: str, user_id: str | None = None
    ) -> PageInventoryResponse | None:
        await self._maybe_ensure_indexes()
        doc = await self._latest_extraction_doc(lead_id)
        if doc is None:
            lead = await self.get_lead(lead_id, user_id=user_id)
            if lead is None:
                return None
            return PageInventoryResponse(
                leadId=lead_id,
                extractionId=None,
                crawlStatus="idle",
                sitemapStatus="unknown",
                detectedWebsiteUrl=lead.detectedWebsiteUrl,
                pagesDiscovered=0,
                pagesCrawled=0,
                pages=[],
                gapItems=["crawl_not_started"],
                errors=[],
                updatedAt=lead.updatedAt,
            )
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None
        return PageInventoryResponse(
            leadId=str(doc["leadId"]),
            extractionId=str(doc["id"]),
            crawlStatus=doc["crawlStatus"],
            sitemapStatus=doc["sitemapStatus"],
            detectedWebsiteUrl=doc.get("detectedWebsiteUrl"),
            pagesDiscovered=int(doc.get("pagesDiscovered", 0)),
            pagesCrawled=int(doc.get("pagesCrawled", 0)),
            pages=list(doc.get("pageInventory", [])),
            gapItems=list(doc.get("gapItems", [])),
            errors=list(doc.get("errors", [])),
            updatedAt=_utc(doc["updatedAt"]) or _now(),
        )

    # Analysis Methods

    async def get_analysis(
        self, lead_id: str, user_id: str | None = None
    ) -> ExtractionAnalysisResponse | None:
        """Get the latest analysis for a lead's extraction."""
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None
        doc = await self._latest_extraction_doc(lead_id)
        if doc is None:
            return None
        analysis_data = doc.get("analysis")
        if not analysis_data:
            return None
        return ExtractionAnalysisResponse(
            analysis=ExtractionAnalysis(**analysis_data)
            if isinstance(analysis_data, dict)
            else analysis_data,
            extractionId=str(doc["id"]),
            extractionVersion=int(doc.get("version", 1)),
        )

    async def get_analysis_version(
        self, lead_id: str, extraction_id: str, version: int
    ) -> ExtractionAnalysisResponse | None:
        """Load analysis from the exact extraction version pinned by a run."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = self._extractions.get(lead_id, [])
                doc = next((d for d in docs if str(d.get("id")) == extraction_id and int(d.get("version", 0)) == version), None)
        else:
            doc = await database["site_extractions"].find_one({"id": extraction_id, "leadId": lead_id, "version": version})
        if not doc or not doc.get("analysis"):
            return None
        return ExtractionAnalysisResponse(
            analysis=ExtractionAnalysis(**doc["analysis"]),
            extractionId=str(doc["id"]),
            extractionVersion=int(doc.get("version", 1)),
        )

    async def start_analysis_refresh(
        self, lead_id: str, user_id: str | None = None
    ) -> ExtractionJobResponse | None:
        """Re-run LLM analysis on existing extraction without re-crawling."""
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None

        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.crawlStatus not in (
            "completed",
            "partial",
        ):
            raise ValueError("extraction_not_completed")

        # Prevent duplicate analysis jobs
        database = get_database()
        if database is not None:
            existing_job = await database["jobs"].find_one(
                {
                    "leadId": lead_id,
                    "jobType": "analysis_refresh",
                    "status": {"$in": ["queued", "running"]},
                }
            )
            if existing_job is not None:
                logger.info(
                    "Analysis refresh already in progress for lead %s (job %s)",
                    lead_id,
                    existing_job["id"],
                )
                return ExtractionJobResponse(
                    job=_job_doc_to_summary(existing_job), extraction=extraction
                )
        else:
            # In-memory duplicate check
            async with self._memory_lock:
                for job_id, job_doc in self._jobs.items():
                    if (
                        job_doc.get("leadId") == lead_id
                        and job_doc.get("jobType") == "analysis_refresh"
                        and job_doc.get("status") in ["queued", "running"]
                    ):
                        logger.info(
                            "Analysis refresh already in progress for lead %s (job %s)",
                            lead_id,
                            job_id,
                        )
                        return ExtractionJobResponse(
                            job=_job_doc_to_summary(job_doc), extraction=extraction
                        )

        job = await self._create_job(
            lead_ids=[lead_id],
            job_type="analysis_refresh",
            status="queued",
            progress=0,
            step="Queued for analysis refresh",
            metadata={"leadId": lead_id, "extractionId": extraction.id},
        )

        self._dispatch_analysis_job(job_id=job.id, lead_id=lead_id)

        return ExtractionJobResponse(job=job, extraction=extraction)

    def _dispatch_analysis_job(self, *, job_id: str, lead_id: str) -> None:
        """Dispatch analysis refresh job to Celery."""
        from app.core.celery_app import celery_app

        celery_app.send_task(
            "lenquant.jobs.run_analysis_refresh",
            args=[lead_id, job_id],
        )

    async def run_analysis_refresh_job(self, *, lead_id: str, job_id: str) -> None:
        """Run the analysis refresh job (called by Celery task)."""
        await self._update_job(
            job_id,
            status="running",
            progress=20,
            step="Loading extraction data",
            lead_ids=[lead_id],
        )

        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.crawlStatus not in (
            "completed",
            "partial",
        ):
            await self._update_job(
                job_id,
                status="failed",
                progress=100,
                step="Extraction not available",
                finished=True,
                lead_ids=[lead_id],
                error_message="No completed extraction found for analysis",
            )
            return

        await self._update_job(
            job_id,
            status="running",
            progress=50,
            step="Running LLM analysis",
            lead_ids=[lead_id],
        )

        try:
            analysis_result = await analyze_extraction(extraction)
        except Exception as exc:
            logger.error("Analysis refresh failed for lead %s: %s", lead_id, exc)
            await self._update_job(
                job_id,
                status="failed",
                progress=100,
                step="Analysis failed",
                finished=True,
                lead_ids=[lead_id],
                error_message=str(exc).splitlines()[0],
            )
            return

        # Save analysis to extraction doc
        database = get_database()
        if database is not None:
            await database["site_extractions"].find_one_and_update(
                {"leadId": lead_id},
                {
                    "$set": {
                        "analysis": analysis_result,
                        "updatedAt": _now(),
                    }
                },
                sort=[("version", -1)],
            )

        await self._update_job(
            job_id,
            status="completed",
            progress=100,
            step="Analysis complete",
            finished=True,
            lead_ids=[lead_id],
        )
        logger.info("Analysis refresh complete for lead %s", lead_id)

    # Master Brief Methods (AI-Native)

    async def _latest_master_brief_doc(self, lead_id: str) -> dict[str, Any] | None:
        """Get the latest master brief document from storage."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                briefs = self._memory.get("master_briefs", {}).get(lead_id, [])
                return briefs[-1] if briefs else None
        else:
            doc = await database["master_briefs"].find_one(
                {"leadId": lead_id},
                sort=[("version", -1)],
            )
            return doc

    async def get_master_brief(self, lead_id: str) -> MasterBrief | None:
        """Get the current master brief for a lead."""
        await self._maybe_ensure_indexes()
        doc = await self._latest_master_brief_doc(lead_id)
        if doc is None:
            return None
        return MasterBrief.model_validate(doc)

    async def create_master_brief(
        self, lead_id: str, user_id: str | None = None
    ) -> MasterBrief | None:
        """Generate a new AI master brief from extraction data."""
        from app.core.master_brief import generate_master_brief

        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None

        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("brief_requires_extraction")

        # Generate master brief using AI
        master_brief = await generate_master_brief(
            lead_id=lead_id,
            extraction=extraction,
        )

        # Store in database
        doc = master_brief.model_dump()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._memory.setdefault("master_briefs", {}).setdefault(
                    lead_id, []
                ).append(doc)
        else:
            await database["master_briefs"].insert_one(doc)

        await self._record_brief_event(
            lead_id,
            event_type="master_brief_created",
            event_name="Master brief generated",
            version=master_brief.version,
        )

        return master_brief

    async def refine_master_brief(
        self, lead_id: str, feedback: str, user_id: str | None = None
    ) -> MasterBrief | None:
        """Refine master brief with user feedback."""
        from app.core.master_brief import generate_master_brief

        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None

        previous_brief = await self.get_master_brief(lead_id)
        if previous_brief is None:
            raise ValueError("no_existing_brief")

        extraction = await self.get_extraction(lead_id)
        if extraction is None:
            return None

        # Regenerate with feedback
        master_brief = await generate_master_brief(
            lead_id=lead_id,
            extraction=extraction,
            feedback=feedback,
            previous_brief=previous_brief,
        )

        # Store new version
        doc = master_brief.model_dump()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._memory.setdefault("master_briefs", {}).setdefault(
                    lead_id, []
                ).append(doc)
        else:
            await database["master_briefs"].insert_one(doc)

        await self._record_brief_event(
            lead_id,
            event_type="master_brief_refined",
            event_name="Master brief refined",
            version=master_brief.version,
        )

        return master_brief

    async def approve_master_brief(
        self,
        lead_id: str,
        approved_by: str,
        notes: str | None = None,
        user_id: str | None = None,
    ) -> MasterBrief | None:
        """Approve the master brief to trigger site generation."""
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            raise ValueError("no_existing_brief")
        brief = await self.get_master_brief(lead_id)
        if brief is None:
            raise ValueError("no_existing_brief")

        # Create new version with approved state
        doc = brief.model_dump()
        doc["approvalState"] = "approved"
        doc["approvedAt"] = _now()
        doc["approvedBy"] = approved_by
        if notes:
            doc["reviewNotes"] = notes
        doc["updatedAt"] = _now()

        # Store updated version
        database = get_database()
        if database is None:
            async with self._memory_lock:
                briefs = self._memory.setdefault("master_briefs", {}).setdefault(
                    lead_id, []
                )
                # Replace last version
                if briefs:
                    briefs[-1] = doc
                else:
                    briefs.append(doc)
        else:
            # Update in place
            await database["master_briefs"].update_one(
                {"id": brief.id},
                {
                    "$set": {
                        "approvalState": "approved",
                        "approvedAt": doc["approvedAt"],
                        "approvedBy": approved_by,
                        "reviewNotes": notes,
                        "updatedAt": doc["updatedAt"],
                    }
                },
            )

        await self._record_brief_event(
            lead_id,
            event_type="master_brief_approved",
            event_name="Master brief approved",
            version=brief.version,
        )

        # Log pipeline event for brief approval
        await self.log_pipeline_event(
            lead_id,
            event_type="brief_approved",
            status="success",
            message="Brief approved",
            detail=f"Approved by {approved_by}" + (f": {notes}" if notes else ""),
            metadata={"approvedBy": approved_by, "briefVersion": brief.version},
        )

        # Advance pipeline to generating
        await self.advance_pipeline_after_brief(lead_id)

        return MasterBrief.model_validate(doc)

    async def get_master_brief_version(
        self, lead_id: str, brief_id: str, version: int
    ) -> MasterBrief | None:
        """Load the exact approved brief pinned by a generation run."""
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = self._memory.get("master_briefs", {}).get(lead_id, [])
                doc = next((d for d in docs if str(d.get("id")) == brief_id and int(d.get("version", 0)) == version), None)
        else:
            doc = await database["master_briefs"].find_one({"id": brief_id, "leadId": lead_id, "version": version})
        return MasterBrief.model_validate(doc) if doc else None

    async def update_master_brief_assets(
        self, lead_id: str, assets: dict[str, Any], user_id: str | None = None
    ) -> MasterBrief | None:
        """Persist operator corrections to brand assets before approval."""
        if await self.get_lead(lead_id, user_id=user_id) is None:
            return None
        brief = await self.get_master_brief(lead_id)
        if brief is None:
            return None
        merged = brief.brandAssets.model_dump()
        merged.update({key: value for key, value in assets.items() if value is not None})
        database = get_database()
        now = _now()
        if database is None:
            async with self._memory_lock:
                records = self._memory.setdefault("master_briefs", {}).get(lead_id, [])
                if records:
                    records[-1]["brandAssets"] = merged
                    records[-1]["updatedAt"] = now
        else:
            await database["master_briefs"].update_one(
                {"id": brief.id}, {"$set": {"brandAssets": merged, "updatedAt": now}}
            )
        return brief.model_copy(update={"brandAssets": merged, "updatedAt": now})

    async def start_extraction(
        self, lead_id: str, *, refresh: bool = False, user_id: str | None = None
    ) -> ExtractionJobResponse | None:
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id, user_id=user_id)
        if lead is None:
            return None

        # Prevent duplicate jobs: check if extraction is already queued or running
        database = get_database()
        if database is not None:
            existing_job = await database["jobs"].find_one(
                {
                    "leadId": lead_id,
                    "jobType": {"$in": ["site_crawl", "site_refresh"]},
                    "status": {"$in": ["queued", "running"]},
                }
            )
            if existing_job is not None:
                logger.info(
                    "Extraction already in progress for lead %s (job %s)",
                    lead_id,
                    existing_job["id"],
                )
                # Return the existing job instead of creating a new one
                existing_snapshot = await self.get_extraction(lead_id)
                return ExtractionJobResponse(
                    job=_job_doc_to_summary(existing_job), extraction=existing_snapshot
                )
        else:
            # In-memory duplicate check
            async with self._memory_lock:
                for job_id, job_doc in self._jobs.items():
                    if (
                        job_doc.get("leadId") == lead_id
                        and job_doc.get("jobType") in ["site_crawl", "site_refresh"]
                        and job_doc.get("status") in ["queued", "running"]
                    ):
                        logger.info(
                            "Extraction already in progress for lead %s (job %s)",
                            lead_id,
                            job_id,
                        )
                        existing_snapshot = await self.get_extraction(lead_id)
                        return ExtractionJobResponse(
                            job=_job_doc_to_summary(job_doc),
                            extraction=existing_snapshot,
                        )

        job_type = "site_refresh" if refresh else "site_crawl"
        job = await self._create_job(
            lead_ids=[lead_id],
            job_type=job_type,
            status="queued",
            progress=0,
            step="Queued for extraction",
            metadata={
                "mode": "refresh" if refresh else "start",
                "leadWebsiteUrl": lead.websiteUrl,
            },
        )

        existing_snapshot = await self.get_extraction(lead_id)
        await self._dispatch_extraction_job(
            job_id=job.id, lead_id=lead_id, refresh=refresh
        )

        return ExtractionJobResponse(job=job, extraction=existing_snapshot)

    async def run_extraction_job(
        self, *, lead_id: str, job_id: str, refresh: bool
    ) -> None:
        # Initialize checkpointing
        checkpoint = TaskCheckpoint(job_id, "extraction")

        # Check for existing checkpoint
        stage, progress, state = await resume_or_start_task(
            job_id, "extraction", "start"
        )

        lead = await self.get_lead(lead_id)
        if lead is None:
            await self._update_job(
                job_id,
                status="failed",
                progress=100,
                step="Lead missing for extraction",
                finished=True,
                lead_ids=[lead_id],
                error_message="Lead not found",
            )
            return

        # Resume from checkpoint if available
        crawl_data = state.get("crawl_data") if stage != "start" else None

        if crawl_data is None:
            # Stage 1: Crawl website
            await self._update_job(
                job_id,
                status="running",
                progress=5,
                step="Resolving public website",
                lead_ids=[lead_id],
            )
            try:
                crawl_data = await asyncio.to_thread(
                    crawl_website, lead.websiteUrl, lead_company_name=lead.companyName
                )

                # Save checkpoint after crawl
                await checkpoint.save_checkpoint(
                    stage="crawled",
                    progress=30,
                    state={"crawl_data": crawl_data},
                    metadata={"lead_id": lead_id},
                )

            except Exception as exc:  # pragma: no cover - network edge cases
                import traceback

                # Capture full error details
                error_type = type(exc).__name__
                error_msg = str(exc)
                tb_lines = traceback.format_exc().split("\n")[-6:]
                tb_summary = "\n".join(tb_lines).strip()

                await self._update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    step="Extraction worker failed",
                    finished=True,
                    lead_ids=[lead_id],
                    error_message=str(exc).splitlines()[0],
                )

                # Log detailed error to pipeline events
                await self.log_pipeline_event(
                    lead_id,
                    event_type="extraction_failed",
                    status="error",
                    message=f"Crawl failed: {error_type}",
                    detail=f"{error_msg}\n\nTraceback:\n{tb_summary}",
                    job_id=job_id,
                    metadata={"errorType": error_type, "errorMessage": error_msg},
                )

                await checkpoint.delete_checkpoint()
                return

        # Phase 1: Validate + LLM-enrich extraction if content is sparse
        is_valid, content_issues = validate_extraction_content(crawl_data)
        if not is_valid:
            logging.getLogger("lenquant.jobs").info(
                "Extraction content sparse for %s: %s — running LLM enrichment",
                lead_id,
                content_issues,
            )
            await self._update_job(
                job_id,
                progress=60,
                step="Enriching extraction with LLM analysis",
                lead_ids=[lead_id],
            )
            try:
                await enrich_extraction(crawl_data)
            except Exception as enrich_err:
                logging.getLogger("lenquant.jobs").warning(
                    "LLM enrichment failed: %s", enrich_err
                )

        # Phase 2: ALWAYS analyze extraction with LLM
        await self._update_job(
            job_id,
            progress=70,
            step="Analyzing extraction with LLM",
            lead_ids=[lead_id],
        )

        try:
            # Convert crawl_data to ExtractionSnapshot for analysis
            temp_snapshot = self._extraction_doc_to_snapshot(
                {
                    "id": f"temp-{lead_id}",
                    **crawl_data,
                    "leadId": lead_id,
                    "analysis": None,
                    "createdAt": _now(),
                    "updatedAt": _now(),
                }
            )

            # Run LLM analysis
            analysis_result = await analyze_extraction(temp_snapshot)

            # Store analysis in crawl_data
            crawl_data["analysis"] = {
                **analysis_result,
                "analyzedAt": _now().isoformat(),
            }

            logger.info(
                "LLM analysis complete for %s: %d services, confidence=%d",
                lead_id,
                len(analysis_result.get("services", [])),
                analysis_result.get("confidence", 0),
            )

        except Exception as analysis_err:
            logger.warning(
                "LLM analysis failed, continuing with extraction: %s", analysis_err
            )
            # Don't fail the job, just log and continue
            crawl_data["analysis"] = {
                "services": [],
                "tone": "Professional",
                "primaryCTAs": [],
                "audience": "",
                "valueProposition": "",
                "positioning": "",
                "confidence": 0,
                "analyzedAt": None,
            }

        now = _now()
        previous_doc = await self._latest_extraction_doc(lead_id)
        version = int(previous_doc.get("version", 0)) + 1 if previous_doc else 1
        doc = {
            "id": uuid4().hex,
            "leadId": lead_id,
            "jobId": job_id,
            "version": version,
            "crawlStatus": crawl_data["crawlStatus"],
            "sitemapStatus": crawl_data["sitemapStatus"],
            "pagesDiscovered": crawl_data["pagesDiscovered"],
            "pagesCrawled": crawl_data["pagesCrawled"],
            "canonicalWebsiteUrl": crawl_data["canonicalWebsiteUrl"],
            "detectedWebsiteUrl": crawl_data["detectedWebsiteUrl"],
            "summary": crawl_data["summary"],
            "pageInventory": crawl_data["pageInventory"],
            "sourceCitations": crawl_data["sourceCitations"],
            "brandAssetCues": crawl_data["brandAssetCues"],
            "assetManifest": crawl_data.get("assetManifest", []),
            "sectionInventory": crawl_data.get("sectionInventory", []),
            "visualCaptureSummary": crawl_data.get("visualCaptureSummary", {}),
            "sitemapUrls": crawl_data["sitemapUrls"],
            "confidenceScore": crawl_data["confidenceScore"],
            "gapItems": crawl_data["gapItems"],
            "errors": crawl_data["errors"],
            "analysis": crawl_data.get("analysis"),
            # Enhanced extraction data
            "extractedTestimonials": crawl_data.get("extractedTestimonials", []),
            "extractedClientLogos": crawl_data.get("extractedClientLogos", []),
            "extractedFonts": crawl_data.get("extractedFonts", []),
            "extractedImages": crawl_data.get("extractedImages", []),
            "crawlBudgetUsed": crawl_data.get("crawlBudgetUsed", 0),
            "crawlBudgetLimit": crawl_data.get(
                "crawlBudgetLimit", get_settings().crawl_budget_bytes
            ),
            "crawlTimeElapsedSeconds": crawl_data.get("crawlTimeElapsedSeconds"),
            "assetCacheStats": crawl_data.get("assetCacheStats", {}),
            "assetRetentionDays": get_settings().asset_retention_days,
            "createdAt": previous_doc["createdAt"] if previous_doc else now,
            "updatedAt": now,
        }

        await self._update_job(
            job_id,
            progress=70,
            step="Packaging extraction snapshot",
            lead_ids=[lead_id],
        )

        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._extractions.setdefault(lead_id, []).append(doc)
                lead_doc = self._memory.get(lead_id)
                if lead_doc is not None:
                    lead_doc["latestExtractionId"] = doc["id"]
                    lead_doc["detectedWebsiteUrl"] = doc["detectedWebsiteUrl"]
                    lead_doc["updatedAt"] = now
        else:
            await database["site_extractions"].insert_one(doc)
            await database["leads"].update_one(
                {"id": lead_id},
                {
                    "$set": {
                        "latestExtractionId": doc["id"],
                        "detectedWebsiteUrl": doc["detectedWebsiteUrl"],
                        "updatedAt": now,
                    }
                },
            )

        final_status = (
            "failed" if crawl_data["crawlStatus"] == "failed" else "completed"
        )
        final_step = (
            "Extraction failed"
            if final_status == "failed"
            else (
                "Extraction complete"
                if not crawl_data["gapItems"]
                else "Extraction complete with gaps"
            )
        )
        error_message = (
            crawl_data["errors"][0]
            if final_status == "failed" and crawl_data["errors"]
            else None
        )
        await self._update_job(
            job_id,
            status=final_status,
            progress=100,
            step=final_step,
            finished=True,
            lead_ids=[lead_id],
            error_message=error_message,
        )

        # Delete checkpoint on successful completion
        await checkpoint.delete_checkpoint()

        # Advance the auto-pipeline after extraction completes
        try:
            await self.advance_pipeline_after_extraction(lead_id)
        except Exception:  # pragma: no cover
            logging.getLogger("lenquant.pipeline").exception(
                "Pipeline advance after extraction failed for lead %s", lead_id
            )

    async def _dispatch_extraction_job(
        self, *, job_id: str, lead_id: str, refresh: bool
    ) -> None:
        settings = get_settings()
        if settings.celery_task_always_eager:
            try:
                await self.run_extraction_job(
                    lead_id=lead_id, job_id=job_id, refresh=refresh
                )
            except Exception:  # pragma: no cover - eager path logging
                logging.getLogger("lenquant.jobs").exception(
                    "Inline job extraction:%s:%s failed", lead_id, job_id
                )
                raise
            return

        from app.core.tasks import run_extraction_job_task

        run_extraction_job_task.delay(lead_id=lead_id, job_id=job_id, refresh=refresh)  # type: ignore[attr-defined]

    @staticmethod
    def log_inline_error(label: str, task: asyncio.Task[None]) -> None:
        try:
            exception = task.exception()
        except asyncio.CancelledError:  # pragma: no cover - cancellation log
            logging.getLogger("lenquant.jobs").warning(
                "Inline job %s was cancelled", label
            )
            return
        if exception is None:
            return
        logging.getLogger("lenquant.jobs").exception(
            "Inline job %s failed", label, exc_info=exception
        )


lead_repository = LeadRepository()
