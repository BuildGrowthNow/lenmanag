from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
from datetime import datetime, timezone
from typing import Any, Iterable, Optional
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from app.core.analytics import analytics_repository
from app.core.config import get_settings
from app.core.extraction import crawl_website
from app.core.extraction_enrichment import enrich_extraction, validate_extraction_content
from app.core.mongo import get_database
from app.schemas.brief import (
    BriefSourceKind,
    SiteBrief,
    SiteBriefPatchRequest,
)
from app.schemas.extraction import (
    ExtractionJobResponse,
    ExtractionSnapshot,
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
    SourceReference,
)


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


def _brief_asset_provenance(asset_cues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _unique_by_key(
        [_asset_reference_from_cue(cue) for cue in asset_cues], _brief_reference_key
    )


def _brief_evidence(
    *,
    source_kind: BriefSourceKind,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "sourceKind": source_kind,
        "inferenceLabel": inference_label,
        "confidence": confidence,
        "references": references or [],
    }


def _brief_text_recommendation(
    *,
    value: str,
    source_kind: BriefSourceKind,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "evidence": _brief_evidence(
            source_kind=source_kind,
            inference_label=inference_label,
            confidence=confidence,
            references=references,
        ),
    }


def _brief_section_recommendation(
    *,
    title: str,
    rationale: str,
    source_kind: BriefSourceKind,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "rationale": rationale,
        "evidence": _brief_evidence(
            source_kind=source_kind,
            inference_label=inference_label,
            confidence=confidence,
            references=references,
        ),
    }


def _brief_proof_point(
    *,
    label: str,
    detail: str,
    source_kind: BriefSourceKind,
    inference_label: str,
    confidence: int,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "label": label,
        "detail": detail,
        "evidence": _brief_evidence(
            source_kind=source_kind,
            inference_label=inference_label,
            confidence=confidence,
            references=references,
        ),
    }


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
    return LeadDetail(
        id=str(doc["id"]),
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
        websiteUrl=doc["websiteUrl"],
        normalizedWebsiteUrl=doc["normalizedWebsiteUrl"],
        normalizedDomain=doc["normalizedDomain"],
        detectedWebsiteUrl=doc.get("detectedWebsiteUrl"),
        status=doc["status"],
        industry=doc.get("industry"),
        notes=doc.get("notes"),
        missingFields=list(doc.get("missingFields", [])),
        version=int(doc.get("version", 1)),
        latestJob=latest_job,
        jobs=[_job_doc_to_summary(job) for job in (jobs or [])],
        createdAt=_utc(doc["createdAt"]) or _now(),
        updatedAt=_utc(doc["updatedAt"]) or _now(),
        archivedAt=_serialize_datetime(doc.get("archivedAt")),
    )


def _lead_doc_to_list_item(
    doc: dict[str, Any], latest_job: dict[str, Any] | None = None
) -> LeadListItem:
    return LeadListItem(
        id=str(doc["id"]),
        sourceType=doc["sourceType"],
        companyName=doc.get("companyName"),
        websiteUrl=doc["websiteUrl"],
        normalizedDomain=doc["normalizedDomain"],
        status=doc["status"],
        industry=doc.get("industry"),
        notes=doc.get("notes"),
        missingFields=list(doc.get("missingFields", [])),
        version=int(doc.get("version", 1)),
        latestJob=_job_doc_to_summary(latest_job) if latest_job else None,
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


def _build_lead_doc(
    *,
    source_type: str,
    source_ref: str | None,
    company_name: str | None,
    website_url: str,
    normalized_url: str,
    normalized_domain: str,
    industry: str | None,
    notes: str | None,
) -> dict[str, Any]:
    now = _now()
    lead = {
        "id": uuid4().hex,
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
    def __init__(self) -> None:
        self._memory_lock = asyncio.Lock()
        self._memory: dict[str, dict[str, Any]] = {}
        self._jobs: dict[str, dict[str, Any]] = {}
        self._extractions: dict[str, list[dict[str, Any]]] = {}
        self._briefs: dict[str, list[dict[str, Any]]] = {}
        self._memory_ready = False

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

    async def create_lead(self, request: LeadUpsertRequest) -> LeadActionResponse:
        normalized_url, normalized_domain = _normalize_input_url(request.websiteUrl)
        incoming = _build_lead_doc(
            source_type="manual",
            source_ref=None,
            company_name=request.companyName.strip() if request.companyName else None,
            website_url=normalized_url,
            normalized_url=normalized_url,
            normalized_domain=normalized_domain,
            industry=request.industry.strip() if request.industry else None,
            notes=request.notes.strip() if request.notes else None,
        )

        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                existing = self._find_duplicate_memory(normalized_domain)
                if existing is not None:
                    merged = _merge_lead_doc(existing, incoming)
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
            return response

        existing = await database["leads"].find_one(
            {"normalizedDomain": normalized_domain, "status": {"$ne": "archived"}}
        )
        if existing:
            merged = _merge_lead_doc(existing, incoming)
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
        return response

    def _find_duplicate_memory(self, normalized_domain: str) -> dict[str, Any] | None:
        for lead in self._memory.values():
            if (
                lead.get("normalizedDomain") == normalized_domain
                and lead.get("status") != "archived"
            ):
                return lead
        return None

    async def import_csv(
        self, *, file_name: str | None, csv_bytes: bytes
    ) -> LeadImportResponse:
        await self._maybe_ensure_indexes()
        text = csv_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = [
            row
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]
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
                    row, source_ref=f"{file_name or 'csv'}:row:{index}"
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
        self, row: dict[str, str], *, source_ref: str | None
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
            {"normalizedDomain": normalized_domain, "status": {"$ne": "archived"}}
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
        await analytics_repository.record_admin_event(
            event_type=event_type,
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
        limit: int = 25,
        offset: int = 0,
    ) -> LeadListResponse:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                items = self._list_memory_leads(
                    q=q, status=status, limit=limit, offset=offset
                )
                total = self._count_memory_leads(q=q, status=status)
                return LeadListResponse(
                    items=items,
                    pagination={"total": total, "limit": limit, "offset": offset},
                )

        query: dict[str, Any] = {}
        if status:
            query["status"] = status
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
        return LeadListResponse(
            items=items, pagination={"total": total, "limit": limit, "offset": offset}
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

    async def _lead_list_item_for_doc(
        self, doc: dict[str, Any], database
    ) -> LeadListItem:
        latest_job = None
        latest_job_id = doc.get("latestJobId")
        if latest_job_id:
            latest_job = await database["jobs"].find_one({"id": latest_job_id})
        return _lead_doc_to_list_item(doc, latest_job)

    async def get_lead(self, lead_id: str) -> LeadDetail | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                doc = self._memory.get(lead_id)
                if doc is None:
                    return None
                jobs = self._jobs_for_lead_memory(lead_id)
                return _lead_doc_to_detail(doc, jobs)

        doc = await database["leads"].find_one({"id": lead_id})
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

    def _jobs_for_lead_memory(self, lead_id: str) -> list[dict[str, Any]]:
        jobs = [job for job in self._jobs.values() if lead_id in job.get("leadIds", [])]
        jobs.sort(key=lambda item: item.get("updatedAt", _now()), reverse=True)
        return jobs[:10]

    def _latest_job_memory(self, job_id: str | None) -> dict[str, Any] | None:
        if not job_id:
            return None
        return self._jobs.get(job_id)

    async def update_lead(
        self, lead_id: str, patch: LeadPatchRequest
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

        doc = await database["leads"].find_one({"id": lead_id})
        if doc is None:
            return None
        updated = self._apply_patch(doc, patch)
        await database["leads"].replace_one({"id": lead_id}, updated)
        return await self.get_lead(lead_id)

    def _apply_patch(
        self, doc: dict[str, Any], patch: LeadPatchRequest
    ) -> dict[str, Any]:
        updated = dict(doc)
        if patch.companyName is not None:
            updated["companyName"] = patch.companyName.strip() or None
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

    async def archive_lead(self, lead_id: str) -> LeadDetail | None:
        return await self.update_lead(lead_id, LeadPatchRequest(status="archived"))

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
    ) -> JobSummary:
        now = _now()
        doc = {
            "id": uuid4().hex,
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

    async def get_job(self, job_id: str) -> JobSummary | None:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                job = self._jobs.get(job_id)
                return _job_doc_to_summary(job) if job else None
        doc = await database["jobs"].find_one({"id": job_id})
        return _job_doc_to_summary(doc) if doc else None

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
                return _job_doc_to_summary(retry_doc)
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
        return await self.get_job(job.id)

    async def get_queue_health(self) -> JobQueueHealthResponse:
        await self._maybe_ensure_indexes()
        database = get_database()
        if database is None:
            async with self._memory_lock:
                docs = list(self._jobs.values())
        else:
            cursor = database["jobs"].find({}).sort("updatedAt", -1).limit(250)
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

    async def delete_lead(self, lead_id: str) -> LeadDetail | None:
        return await self.archive_lead(lead_id)

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
            summary={
                "companyName": lead.companyName,
                "canonicalWebsiteUrl": lead.websiteUrl,
                "detectedWebsiteUrl": lead.detectedWebsiteUrl,
                "positioningSummary": None,
                "audienceClues": [],
                "serviceClues": [],
                "ctaClues": [],
                "toneClues": [],
            },
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
            createdAt=now,
            updatedAt=now,
        )

    async def get_extraction(self, lead_id: str) -> ExtractionSnapshot | None:
        await self._maybe_ensure_indexes()
        doc = await self._latest_extraction_doc(lead_id)
        if doc is None:
            lead = await self.get_lead(lead_id)
            if lead is None:
                return None
            return self._empty_extraction_snapshot(lead)
        return self._extraction_doc_to_snapshot(doc)

    async def list_pages(self, lead_id: str) -> PageInventoryResponse | None:
        await self._maybe_ensure_indexes()
        doc = await self._latest_extraction_doc(lead_id)
        if doc is None:
            lead = await self.get_lead(lead_id)
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

    def _latest_brief_memory(self, lead_id: str) -> dict[str, Any] | None:
        briefs = self._briefs.get(lead_id, [])
        if not briefs:
            return None
        return max(briefs, key=lambda item: item.get("version", 0))

    async def _latest_brief_doc(self, lead_id: str) -> dict[str, Any] | None:
        database = get_database()
        if database is None:
            async with self._memory_lock:
                return self._latest_brief_memory(lead_id)
        return await database["site_briefs"].find_one(
            {"leadId": lead_id}, sort=[("version", -1)]
        )

    def _brief_doc_to_snapshot(self, doc: dict[str, Any]) -> SiteBrief:
        company_summary = doc.get("companySummary")
        value_proposition_summary = (
            doc.get("valuePropositionSummary") or company_summary
        )
        return SiteBrief(
            id=str(doc["id"]),
            leadId=str(doc["leadId"]),
            sourceExtractionId=str(doc["sourceExtractionId"]),
            sourceExtractionVersion=int(doc.get("sourceExtractionVersion", 0)),
            version=int(doc.get("version", 1)),
            approvalState=doc["approvalState"],
            needsReview=bool(doc.get("needsReview", True)),
            companySummary=company_summary,
            valuePropositionSummary=value_proposition_summary,
            audienceHypothesis=doc["audienceHypothesis"],
            toneProfile=doc["toneProfile"],
            conversionAngle=doc["conversionAngle"],
            recommendedHero=doc["recommendedHero"],
            recommendedSections=list(doc.get("recommendedSections", [])),
            proofPoints=list(doc.get("proofPoints", [])),
            visualRedesign=list(doc.get("visualRedesign", [])),
            sourceCitations=list(doc.get("sourceCitations", [])),
            brandAssetProvenance=list(doc.get("brandAssetProvenance", [])),
            confidenceScore=int(doc.get("confidenceScore", 0)),
            missingRequirements=list(doc.get("missingRequirements", [])),
            reviewNotes=doc.get("reviewNotes"),
            approvedAt=_serialize_datetime(doc.get("approvedAt")),
            approvedBy=doc.get("approvedBy"),
            createdAt=_utc(doc["createdAt"]) or _now(),
            updatedAt=_utc(doc["updatedAt"]) or _now(),
        )

    def _brief_source_references(
        self,
        *,
        extraction: ExtractionSnapshot,
        asset_cues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        refs = [
            _page_reference_from_citation(citation)
            for citation in extraction.sourceCitations
        ]
        refs.extend(_asset_reference_from_cue(cue) for cue in asset_cues)
        return _unique_by_key(refs, _brief_reference_key)

    def _field_references(
        self,
        *,
        extraction: ExtractionSnapshot,
        asset_cues: list[dict[str, Any]],
        evidence_types: list[str] | None = None,
        include_assets: bool = False,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        refs = []
        if evidence_types:
            refs.extend(
                _page_reference_from_citation(citation)
                for citation in extraction.sourceCitations
                if _as_plain_dict(citation).get("evidenceType") in evidence_types
            )
        else:
            refs.extend(
                _page_reference_from_citation(citation)
                for citation in extraction.sourceCitations
            )
        if include_assets:
            refs.extend(_asset_reference_from_cue(cue) for cue in asset_cues)
        deduped = _unique_by_key(refs, _brief_reference_key)
        return deduped[:limit]

    def _brief_confidence(self, *scores: int, floor: int = 0, ceiling: int = 95) -> int:
        values = [score for score in scores if score is not None]
        if not values:
            return floor
        return max(floor, min(ceiling, round(sum(values) / len(values))))

    def _build_brief_doc(
        self,
        *,
        lead: LeadDetail,
        extraction: ExtractionSnapshot,
        previous_brief: dict[str, Any] | None = None,
        patch: SiteBriefPatchRequest | None = None,
        approved_by: str | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        now = _now()
        asset_cues = [
            cue.model_dump() if hasattr(cue, "model_dump") else cue
            for cue in extraction.brandAssetCues
        ]
        source_refs = self._brief_source_references(
            extraction=extraction, asset_cues=asset_cues
        )
        previous_version = (
            int(previous_brief.get("version", 0)) if previous_brief else 0
        )
        next_version = previous_version + 1

        positioning = extraction.summary.positioningSummary
        company_summary_value = positioning or (
            f"{lead.companyName} is the lead record for {lead.websiteUrl}."
            if lead.companyName
            else f"Public positioning for {lead.websiteUrl} is sparse in the current crawl."
        )
        company_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["title", "meta"],
            limit=2,
        )
        company_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in company_refs),
            floor=38,
        )
        company_source_kind: BriefSourceKind = (
            "source_backed" if positioning else "inferred"
        )
        company_inference = (
            "Summarized directly from homepage title and meta description."
            if positioning
            else "Inferred from lead identity and sparse public content."
        )

        value_proposition_signal = extraction.summary.positioningSummary or (
            extraction.summary.serviceClues[0]
            if extraction.summary.serviceClues
            else ""
        )
        value_proposition_value = (
            value_proposition_signal
            if value_proposition_signal
            else "The crawl did not expose a clear value proposition, so the operator should review the positioning before generation."
        )
        value_proposition_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["title", "meta", "heading"],
            include_assets=True,
            limit=3,
        )
        value_proposition_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in value_proposition_refs),
            floor=35,
        )

        audience_signal = (
            ", ".join(extraction.summary.audienceClues[:3])
            if extraction.summary.audienceClues
            else ""
        )
        audience_value = (
            f"Primary audience signals point to {audience_signal}."
            if audience_signal
            else "Audience is not explicit in the public crawl and needs operator review."
        )
        audience_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["heading", "meta", "title"],
            limit=2,
        )
        audience_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in audience_refs),
            floor=32,
        )

        tone_signal = (
            ", ".join(extraction.summary.toneClues[:3])
            if extraction.summary.toneClues
            else ""
        )
        if not tone_signal and asset_cues:
            tone_signal = ", ".join(cue["label"] for cue in asset_cues[:2])
        tone_value = (
            f"Tone cues suggest {tone_signal}."
            if tone_signal
            else "Tone is not explicit in the crawl and should stay conservative until reviewed."
        )
        tone_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["cta", "heading", "title"],
            include_assets=True,
            limit=3,
        )
        tone_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in tone_refs),
            floor=30,
        )

        conversion_signal = (
            extraction.summary.ctaClues[0]
            if extraction.summary.ctaClues
            else (
                extraction.summary.serviceClues[0]
                if extraction.summary.serviceClues
                else ""
            )
        )
        conversion_value = (
            f"Lead with {conversion_signal} and keep the next step simple."
            if conversion_signal
            else "Conversion angle is not explicit in the public site and remains a review item."
        )
        conversion_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["cta", "heading"],
            limit=2,
        )
        conversion_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in conversion_refs),
            floor=34,
        )

        hero_value = (
            f"Use the strongest public positioning statement as the hero anchor: {positioning}"
            if positioning
            else "Use the strongest page title or headline as the hero anchor and keep the rest of the message minimal."
        )
        hero_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["title", "heading", "meta"],
            include_assets=True,
            limit=3,
        )
        hero_confidence = self._brief_confidence(
            extraction.confidenceScore,
            *(ref["confidence"] for ref in hero_refs),
            floor=28,
        )

        section_refs = self._field_references(
            extraction=extraction,
            asset_cues=asset_cues,
            evidence_types=["heading", "cta", "title"],
            include_assets=True,
            limit=3,
        )
        section_items: list[dict[str, Any]] = [
            _brief_section_recommendation(
                title="Hero",
                rationale="Anchor the page with the strongest source-backed positioning statement before adding any secondary content.",
                source_kind="source_backed" if positioning else "inferred",
                inference_label="Derived from homepage positioning and page title signals.",
                confidence=self._brief_confidence(
                    extraction.confidenceScore,
                    *(ref["confidence"] for ref in section_refs),
                    floor=58,
                ),
                references=section_refs,
            )
        ]
        source_sections = [
            section.model_dump() if hasattr(section, "model_dump") else section
            for section in getattr(extraction, "sectionInventory", [])
        ]
        section_type_labels = {
            "services": "Services or Offerings",
            "proof": "Proof and Trust",
            "about": "About / Point of View",
            "process": "Process",
            "pricing": "Packages or Pricing",
            "gallery": "Work / Gallery",
            "contact": "Contact Path",
        }
        seen_section_titles = {"hero"}
        for source_section in source_sections[:10]:
            section_type = str(source_section.get("type") or "unknown")
            if section_type in {"hero", "header", "footer", "unknown"}:
                continue
            raw_title = section_type_labels.get(
                section_type, source_section.get("heading") or "Source Section"
            )
            # Sanitize title for public display
            title = _sanitize_section_title(raw_title)
            if title is None:
                continue  # Skip sections with internal-only titles
            key = title.lower()
            if key in seen_section_titles:
                continue
            seen_section_titles.add(key)
            notes = "; ".join(source_section.get("improvementNotes") or [])
            excerpt = str(
                source_section.get("text") or source_section.get("heading") or ""
            )[:260]
            rationale = f"Redesign the existing {section_type} section around source content: {excerpt}"
            if notes:
                rationale = f"{rationale}. Improvement focus: {notes}"
            section_items.append(
                _brief_section_recommendation(
                    title=title,
                    rationale=rationale,
                    source_kind="source_backed",
                    inference_label="Derived from parsed source page sections and section-level improvement notes.",
                    confidence=self._brief_confidence(
                        extraction.confidenceScore,
                        int(source_section.get("confidence") or 55),
                        floor=56,
                    ),
                    references=section_refs[:2],
                )
            )
        if extraction.summary.serviceClues:
            section_items.append(
                _brief_section_recommendation(
                    title=_sanitize_section_title("Services or Offerings") or "Services",
                    rationale=f"Surface the public service signal: {extraction.summary.serviceClues[0]}.",
                    source_kind="inferred",
                    inference_label="Inferred from service-oriented page language.",
                    confidence=self._brief_confidence(
                        extraction.confidenceScore,
                        72,
                        *(ref["confidence"] for ref in section_refs[:2]),
                        floor=52,
                    ),
                    references=section_refs[:2],
                )
            )
        if extraction.brandAssetCues:
            sanitized_title = _sanitize_section_title("Brand cues")
            if sanitized_title:  # Only add if not filtered out
                section_items.append(
                    _brief_section_recommendation(
                        title=sanitized_title,
                        rationale="Carry the extracted logo, color, or typography signal into the visual hierarchy.",
                        source_kind="source_backed",
                        inference_label="Supported by captured public brand assets.",
                        confidence=self._brief_confidence(
                            *(cue["confidence"] for cue in asset_cues), floor=54
                        ),
                        references=self._field_references(
                            extraction=extraction,
                            asset_cues=asset_cues,
                            include_assets=True,
                            limit=3,
                        ),
                    )
                )
        if extraction.summary.ctaClues:
            section_items.append(
                _brief_section_recommendation(
                    title=_sanitize_section_title("Conversion path") or "Get Started",
                    rationale=f"Make the primary CTA pattern explicit: {extraction.summary.ctaClues[0]}.",
                    source_kind="inferred",
                    inference_label="Inferred from CTA wording and placement cues.",
                    confidence=self._brief_confidence(
                        extraction.confidenceScore,
                        66,
                        *(ref["confidence"] for ref in section_refs[:2]),
                        floor=50,
                    ),
                    references=section_refs[:2],
                )
            )
        if extraction.gapItems:
            sanitized_gap_title = _sanitize_section_title("Open questions")
            if sanitized_gap_title:  # Only add if not filtered out
                section_items.append(
                    _brief_section_recommendation(
                        title=sanitized_gap_title,
                    rationale="Keep unresolved source gaps visible so the operator can review them before generation starts.",
                    source_kind="inferred",
                    inference_label="Derived from extraction gap items.",
                    confidence=self._brief_confidence(
                        60, extraction.confidenceScore, floor=45
                    ),
                        references=[],
                    )
                )

        proof_points: list[dict[str, Any]] = []
        for reference in source_refs[:4]:
            proof_points.append(
                _brief_proof_point(
                    label=reference["label"],
                    detail=reference["excerpt"],
                    source_kind="source_backed"
                    if reference["kind"] == "page"
                    else "inferred",
                    inference_label="Captured from public source material."
                    if reference["kind"] == "page"
                    else "Captured from public brand assets.",
                    confidence=int(reference["confidence"]),
                    references=[reference],
                )
            )

        missing_requirements = list(dict.fromkeys([*extraction.gapItems]))
        if not extraction.summary.audienceClues:
            missing_requirements.append("audience_hypothesis_needs_review")
        if not extraction.summary.toneClues and not asset_cues:
            missing_requirements.append("tone_profile_needs_review")
        if not extraction.summary.ctaClues:
            missing_requirements.append("conversion_angle_needs_review")
        if not source_refs:
            missing_requirements.append("source_citations_missing")
        if not asset_cues:
            missing_requirements.append("brand_asset_provenance_missing")
        missing_requirements = list(dict.fromkeys(missing_requirements))

        visual_redesigns: list[dict[str, Any]] = []
        for page_item in extraction.pageInventory:
            page_dict = page_item.model_dump() if hasattr(page_item, "model_dump") else page_item
            if not page_dict.get("sections"):
                continue
            
            critiques = []
            for sec in page_dict["sections"]:
                sec_type = sec.get("type", "unknown")
                critiques.append({
                    "sectionType": sec_type,
                    "originalStrengths": ["Captured original content successfully."] if sec.get("text") else [],
                    "originalWeaknesses": sec.get("improvementNotes", []),
                    "redesignGoal": "Make the offer immediately clear and premium." if sec_type == "hero" else "Improve visual hierarchy and premium feel.",
                    "contentToReuse": [sec.get("heading")] if sec.get("heading") else [],
                    "contentToRewrite": [],
                    "recommendedComponent": "HeroSplitEditorial" if sec_type == "hero" else "SectionStandard",
                    "visualDirection": "minimal-luxe",
                    "confidence": sec.get("confidence", 50)
                })
            
            visual_redesigns.append({
                "pageUrl": page_dict["url"],
                "critiques": critiques,
                "artDirection": "minimal-luxe"
            })

        confidence_score = self._brief_confidence(
            company_confidence,
            audience_confidence,
            tone_confidence,
            conversion_confidence,
            hero_confidence,
            extraction.confidenceScore,
        )

        approval_state: str = (
            "approved"
            if approved
            else (
                "needs_review"
                if missing_requirements or confidence_score < 70
                else "draft"
            )
        )
        if patch is not None:
            approval_state = "needs_review"

        def _apply_override(value: str, override: str | None) -> str:
            if override is None:
                return value
            return override.strip()

        company_summary_value = _apply_override(
            company_summary_value, patch.companySummary if patch else None
        )
        value_proposition_value = _apply_override(
            value_proposition_value, patch.valuePropositionSummary if patch else None
        )
        audience_value = _apply_override(
            audience_value, patch.audienceHypothesis if patch else None
        )
        tone_value = _apply_override(tone_value, patch.toneProfile if patch else None)
        conversion_value = _apply_override(
            conversion_value, patch.conversionAngle if patch else None
        )
        hero_value = _apply_override(
            hero_value, patch.recommendedHero if patch else None
        )
        review_notes = (
            patch.reviewNotes.strip()
            if patch and patch.reviewNotes is not None
            else (previous_brief.get("reviewNotes") if previous_brief else None)
        )

        if patch is not None:
            if not company_summary_value.strip():
                missing_requirements.append("company_summary_missing")
                company_confidence = min(company_confidence, 25)
                company_source_kind = "inferred"
                company_inference = "Operator cleared this field during review."
            if not value_proposition_value.strip():
                missing_requirements.append("value_proposition_summary_missing")
                value_proposition_confidence = min(value_proposition_confidence, 25)
            if not audience_value.strip():
                missing_requirements.append("audience_hypothesis_missing")
                audience_confidence = min(audience_confidence, 25)
            if not tone_value.strip():
                missing_requirements.append("tone_profile_missing")
                tone_confidence = min(tone_confidence, 25)
            if not conversion_value.strip():
                missing_requirements.append("conversion_angle_missing")
                conversion_confidence = min(conversion_confidence, 25)
            if not hero_value.strip():
                missing_requirements.append("hero_direction_missing")
                hero_confidence = min(hero_confidence, 25)
            if patch.recommendedSections is not None and not [
                line.strip()
                for line in patch.recommendedSections
                if line and line.strip()
            ]:
                missing_requirements.append("recommended_sections_missing")
        missing_requirements = list(dict.fromkeys(missing_requirements))

        if patch is not None and patch.recommendedSections is not None:
            section_items = [
                _brief_section_recommendation(
                    title=title,
                    rationale="Operator edited the section direction against the preserved source citations.",
                    source_kind="inferred",
                    inference_label="Edited by operator after source review.",
                    confidence=80,
                    references=section_refs[:2],
                )
                for title in [
                    line.strip()
                    for line in patch.recommendedSections
                    if line and line.strip()
                ]
            ]
        elif previous_brief and patch is not None:
            section_items = list(previous_brief.get("recommendedSections", []))

        if patch is not None:
            proof_points = (
                list(previous_brief.get("proofPoints", []))
                if previous_brief
                else proof_points
            )
            source_refs = (
                list(previous_brief.get("sourceCitations", []))
                if previous_brief
                else source_refs
            )
            if company_summary_value != (
                previous_brief.get("companySummary", {}).get("value")
                if previous_brief
                else None
            ):
                company_confidence = max(company_confidence, 70)
            if value_proposition_value != (
                previous_brief.get("valuePropositionSummary", {}).get("value")
                if previous_brief
                else None
            ):
                value_proposition_confidence = max(value_proposition_confidence, 70)
            if audience_value != (
                previous_brief.get("audienceHypothesis", {}).get("value")
                if previous_brief
                else None
            ):
                audience_confidence = max(audience_confidence, 68)
            if tone_value != (
                previous_brief.get("toneProfile", {}).get("value")
                if previous_brief
                else None
            ):
                tone_confidence = max(tone_confidence, 68)
            if conversion_value != (
                previous_brief.get("conversionAngle", {}).get("value")
                if previous_brief
                else None
            ):
                conversion_confidence = max(conversion_confidence, 68)
            if hero_value != (
                previous_brief.get("recommendedHero", {}).get("value")
                if previous_brief
                else None
            ):
                hero_confidence = max(hero_confidence, 68)
            confidence_score = self._brief_confidence(
                company_confidence,
                audience_confidence,
                tone_confidence,
                conversion_confidence,
                hero_confidence,
                extraction.confidenceScore,
                floor=confidence_score,
            )

        brief = {
            "id": uuid4().hex,
            "leadId": lead.id,
            "sourceExtractionId": extraction.id,
            "sourceExtractionVersion": extraction.version,
            "version": next_version,
            "approvalState": approval_state,
            "needsReview": approval_state != "approved",
            "companySummary": _brief_text_recommendation(
                value=company_summary_value,
                source_kind=company_source_kind if patch is None else "inferred",
                inference_label=company_inference
                if patch is None
                else "Operator edited against preserved source evidence.",
                confidence=company_confidence,
                references=company_refs,
            ),
            "valuePropositionSummary": _brief_text_recommendation(
                value=value_proposition_value,
                source_kind="source_backed" if value_proposition_signal else "inferred",
                inference_label="Summarized directly from the public positioning and service language."
                if value_proposition_signal
                else "Inferred from the lead record and sparse crawl signals.",
                confidence=value_proposition_confidence,
                references=value_proposition_refs,
            ),
            "audienceHypothesis": _brief_text_recommendation(
                value=audience_value,
                source_kind="inferred",
                inference_label="Inferred from audience language in the public crawl."
                if patch is None
                else "Operator edited against preserved source evidence.",
                confidence=audience_confidence,
                references=audience_refs,
            ),
            "toneProfile": _brief_text_recommendation(
                value=tone_value,
                source_kind="inferred" if patch is None else "inferred",
                inference_label="Inferred from CTA and brand cues."
                if patch is None
                else "Operator edited against preserved source evidence.",
                confidence=tone_confidence,
                references=tone_refs,
            ),
            "conversionAngle": _brief_text_recommendation(
                value=conversion_value,
                source_kind="inferred",
                inference_label="Inferred from CTA patterns and service language."
                if patch is None
                else "Operator edited against preserved source evidence.",
                confidence=conversion_confidence,
                references=conversion_refs,
            ),
            "recommendedHero": _brief_text_recommendation(
                value=hero_value,
                source_kind="inferred" if patch is None else "inferred",
                inference_label="Recommended from source signals before generation."
                if patch is None
                else "Operator edited against preserved source evidence.",
                confidence=hero_confidence,
                references=hero_refs,
            ),
            "recommendedSections": section_items,
            "proofPoints": proof_points,
            "visualRedesign": visual_redesigns,
            "sourceCitations": source_refs,
            "brandAssetProvenance": _brief_asset_provenance(asset_cues),
            "confidenceScore": confidence_score,
            "missingRequirements": missing_requirements,
            "reviewNotes": review_notes,
            "approvedAt": now if approved else None,
            "approvedBy": approved_by if approved else None,
            "createdAt": now,
            "updatedAt": now,
        }
        if patch is not None and previous_brief is not None:
            brief["sourceExtractionId"] = previous_brief["sourceExtractionId"]
            brief["sourceExtractionVersion"] = int(
                previous_brief.get("sourceExtractionVersion", extraction.version)
            )
            brief["proofPoints"] = list(previous_brief.get("proofPoints", []))
            brief["sourceCitations"] = list(previous_brief.get("sourceCitations", []))
            brief["brandAssetProvenance"] = list(
                previous_brief.get("brandAssetProvenance", [])
            )
            brief["approvedAt"] = None
            brief["approvedBy"] = None
        return brief

    async def get_brief(self, lead_id: str) -> SiteBrief | None:
        await self._maybe_ensure_indexes()
        doc = await self._latest_brief_doc(lead_id)
        if doc is None:
            return None
        return self._brief_doc_to_snapshot(doc)

    async def create_brief(self, lead_id: str) -> SiteBrief | None:
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id)
        if lead is None:
            return None
        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("brief_requires_extraction")
        previous_brief = await self._latest_brief_doc(lead_id)
        doc = self._build_brief_doc(
            lead=lead, extraction=extraction, previous_brief=previous_brief
        )
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._briefs.setdefault(lead_id, []).append(doc)
                snapshot = self._brief_doc_to_snapshot(doc)
        else:
            await database["site_briefs"].insert_one(doc)
            snapshot = self._brief_doc_to_snapshot(doc)
        await self._record_brief_event(
            lead_id,
            event_type="brief_edited",
            event_name="Site brief generated from extraction",
            version=snapshot.version,
        )
        return snapshot

    async def update_brief(
        self, lead_id: str, patch: SiteBriefPatchRequest
    ) -> SiteBrief | None:
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id)
        if lead is None:
            return None
        previous_brief = await self._latest_brief_doc(lead_id)
        if previous_brief is None:
            return None
        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("brief_requires_extraction")
        doc = self._build_brief_doc(
            lead=lead, extraction=extraction, previous_brief=previous_brief, patch=patch
        )
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._briefs.setdefault(lead_id, []).append(doc)
                snapshot = self._brief_doc_to_snapshot(doc)
        else:
            await database["site_briefs"].insert_one(doc)
            snapshot = self._brief_doc_to_snapshot(doc)
        await self._record_brief_event(
            lead_id,
            event_type="brief_edited",
            event_name="Site brief updated",
            version=snapshot.version,
        )
        return snapshot

    async def update_brief_visual_redesign(
        self, lead_id: str, visual_redesign_briefs: list
    ) -> SiteBrief | None:
        """Update brief with visual redesign briefs."""
        await self._maybe_ensure_indexes()
        previous_brief = await self._latest_brief_doc(lead_id)
        if previous_brief is None:
            return None
        
        # Update the brief document with visual redesign
        previous_brief["visualRedesign"] = [
            brief.model_dump() if hasattr(brief, "model_dump") else brief
            for brief in visual_redesign_briefs
        ]
        previous_brief["updatedAt"] = _now()
        
        database = get_database()
        if database is None:
            async with self._memory_lock:
                # Update in memory
                briefs = self._briefs.get(lead_id, [])
                if briefs:
                    briefs[-1] = previous_brief
        else:
            await database["site_briefs"].update_one(
                {"_id": previous_brief["_id"]},
                {"$set": {"visualRedesign": previous_brief["visualRedesign"], "updatedAt": previous_brief["updatedAt"]}},
            )
        
        return self._brief_doc_to_snapshot(previous_brief)

    async def approve_brief(self, lead_id: str, approved_by: str) -> SiteBrief | None:
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id)
        if lead is None:
            return None
        previous_brief = await self._latest_brief_doc(lead_id)
        if previous_brief is None:
            return None
        extraction = await self.get_extraction(lead_id)
        if extraction is None or extraction.version <= 0:
            raise ValueError("brief_requires_extraction")

        # Check for critical extraction gaps that block brief approval
        critical_gaps = [
            "homepage_unreachable",
            "low_confidence_extraction",
            "page_summaries_sparse",
        ]
        if any(gap in extraction.gapItems for gap in critical_gaps):
            raise ValueError("brief_requires_critical_gaps_resolved")
        doc = self._build_brief_doc(
            lead=lead,
            extraction=extraction,
            previous_brief=previous_brief,
            approved_by=approved_by,
            approved=True,
        )
        doc["sourceExtractionId"] = previous_brief["sourceExtractionId"]
        doc["sourceExtractionVersion"] = int(
            previous_brief.get("sourceExtractionVersion", extraction.version)
        )
        doc["proofPoints"] = list(previous_brief.get("proofPoints", []))
        doc["sourceCitations"] = list(previous_brief.get("sourceCitations", []))
        doc["approvalState"] = "approved"
        doc["needsReview"] = False
        doc["approvedAt"] = _now()
        doc["approvedBy"] = approved_by
        database = get_database()
        if database is None:
            async with self._memory_lock:
                self._briefs.setdefault(lead_id, []).append(doc)
                snapshot = self._brief_doc_to_snapshot(doc)
        else:
            await database["site_briefs"].insert_one(doc)
            snapshot = self._brief_doc_to_snapshot(doc)
        await self._record_brief_event(
            lead_id,
            event_type="brief_approved",
            event_name="Site brief approved",
            version=snapshot.version,
        )
        return snapshot

    async def start_extraction(
        self, lead_id: str, *, refresh: bool = False
    ) -> ExtractionJobResponse | None:
        await self._maybe_ensure_indexes()
        lead = await self.get_lead(lead_id)
        if lead is None:
            return None

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
        except Exception as exc:  # pragma: no cover - network edge cases
            await self._update_job(
                job_id,
                status="failed",
                progress=100,
                step="Extraction worker failed",
                finished=True,
                lead_ids=[lead_id],
                error_message=str(exc),
            )
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
            "crawlBudgetUsed": crawl_data.get("crawlBudgetUsed", 0),
            "crawlBudgetLimit": crawl_data.get("crawlBudgetLimit", get_settings().crawl_budget_bytes),
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

        run_extraction_job_task.delay(lead_id=lead_id, job_id=job_id, refresh=refresh)

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
