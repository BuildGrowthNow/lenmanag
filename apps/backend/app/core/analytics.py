from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.mongo import get_database
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    AnalyticsEvent,
    AnalyticsEventCreateRequest,
    AnalyticsMessageMetrics,
    AnalyticsLeadMetrics,
    AnalyticsVariantMetrics,
    AnalyticsSiteMetrics,
    AnalyticsSummary,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class AnalyticsRepository:
    def __init__(self) -> None:
        self._memory_ready = False
        self._memory: list[dict[str, Any]] = []

    async def _maybe_ensure_indexes(self) -> None:
        database = get_database()
        if database is None or self._memory_ready:
            return
        await database["analytics_events"].create_index([("siteId", 1), ("createdAt", -1)])
        await database["analytics_events"].create_index([("leadId", 1), ("createdAt", -1)])
        await database["analytics_events"].create_index([("sessionId", 1), ("createdAt", -1)])
        self._memory_ready = True

    async def ingest_event(self, request: AnalyticsEventCreateRequest) -> AnalyticsEvent:
        await self._maybe_ensure_indexes()
        event = AnalyticsEvent(
            id=uuid4().hex,
            siteId=request.siteId,
            leadId=request.leadId,
            sessionId=request.sessionId,
            visitorFingerprint=request.visitorFingerprint,
            themeKey=request.themeKey,
            variantKey=request.variantKey,
            messageId=request.messageId,
            messageChannel=request.messageChannel,
            eventType=request.eventType,
            eventName=request.eventName,
            pagePath=request.pagePath,
            referrer=request.referrer,
            utm=request.utm,
            metadata=request.metadata,
            createdAt=_now(),
        )
        database = get_database()
        if database is None:
            self._memory.append(event.model_dump())
            return event
        await database["analytics_events"].insert_one(event.model_dump())
        return event

    async def _events(self) -> list[dict[str, Any]]:
        database = get_database()
        if database is None:
            return list(self._memory)
        cursor = database["analytics_events"].find({}).sort("createdAt", -1)
        docs = await cursor.to_list(length=None)
        return [dict(doc) for doc in docs]

    @staticmethod
    def _is_cta_event(event: dict[str, Any]) -> bool:
        return event.get("eventType") in {"hero_cta_click", "secondary_cta_click", "contact_click"}

    @staticmethod
    def _campaign_source(event: dict[str, Any]) -> str | None:
        utm = event.get("utm") or {}
        for key in ("source", "campaign", "medium"):
            value = utm.get(key)
            if value:
                return str(value)
        return None

    @staticmethod
    def _event_source(event: dict[str, Any]) -> str | None:
        return AnalyticsRepository._campaign_source(event) or event.get("referrer")

    @staticmethod
    def _message_key(event: dict[str, Any]) -> str | None:
        if event.get("messageId"):
            return str(event["messageId"])
        if event.get("messageChannel"):
            return str(event["messageChannel"])
        return None

    def _sorted_counter_items(self, counter: Counter) -> list[dict[str, Any]]:
        return [{"value": value, "count": count} for value, count in counter.most_common(10) if value]

    async def get_dashboard(self) -> AnalyticsDashboardResponse:
        events = await self._events()
        total_events = len(events)
        total_page_views = sum(1 for event in events if event.get("eventType") == "page_view")
        total_cta_clicks = sum(1 for event in events if self._is_cta_event(event))
        total_outbound_clicks = sum(1 for event in events if event.get("eventType") == "outbound_link_click")
        total_calendly_clicks = sum(1 for event in events if event.get("eventType") == "calendly_click")
        total_section_exposures = sum(1 for event in events if event.get("eventType") == "section_exposure")
        total_form_interactions = sum(1 for event in events if event.get("eventType") == "form_interaction")
        unique_sessions = len({event.get("sessionId") for event in events if event.get("sessionId")})
        total_sites = len({event.get("siteId") for event in events if event.get("siteId")})
        total_leads = len({event.get("leadId") for event in events if event.get("leadId")})
        events_by_type = Counter(event.get("eventType", "unknown") for event in events)
        pages = Counter(event.get("pagePath") for event in events if event.get("pagePath"))
        sources = Counter(self._event_source(event) for event in events if self._event_source(event))
        referrers = Counter(event.get("referrer") for event in events if event.get("referrer"))
        message_attribution = Counter(self._message_key(event) for event in events if self._message_key(event))
        summary = AnalyticsSummary(
            totalEvents=total_events,
            totalPageViews=total_page_views,
            totalCTAClicks=total_cta_clicks,
            totalOutboundClicks=total_outbound_clicks,
            totalCalendlyClicks=total_calendly_clicks,
            totalSectionExposures=total_section_exposures,
            totalFormInteractions=total_form_interactions,
            uniqueSessions=unique_sessions,
            totalSites=total_sites,
            totalLeads=total_leads,
            eventsByType=dict(events_by_type),
            topPages=[{"pagePath": page, "count": count} for page, count in pages.most_common(10)],
            topSources=self._sorted_counter_items(sources),
            referrers=[{"referrer": ref, "count": count} for ref, count in referrers.most_common(10)],
            messageAttribution=self._sorted_counter_items(message_attribution),
            updatedAt=_now(),
        )
        return AnalyticsDashboardResponse(
            summary=summary,
            siteMetrics=await self._site_metrics(),
            leadMetrics=await self._lead_metrics(),
            variantMetrics=await self._variant_metrics(),
            messageMetrics=await self._message_metrics(),
        )

    async def _site_metrics(self) -> list[AnalyticsSiteMetrics]:
        events = await self._events()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            site_id = event.get("siteId")
            if site_id:
                grouped[str(site_id)].append(event)
        results: list[AnalyticsSiteMetrics] = []
        for site_id, site_events in grouped.items():
            sessions = {event.get("sessionId") for event in site_events if event.get("sessionId")}
            referrers = Counter(event.get("referrer") for event in site_events if event.get("referrer"))
            latest = site_events[0]
            results.append(
                AnalyticsSiteMetrics(
                    siteId=site_id,
                    leadId=next((str(event.get("leadId")) for event in site_events if event.get("leadId")), None),
                    themeKey=next((str(event.get("themeKey")) for event in site_events if event.get("themeKey")), None),
                    variantKey=next((str(event.get("variantKey")) for event in site_events if event.get("variantKey")), None),
                    pageViews=sum(1 for event in site_events if event.get("eventType") == "page_view"),
                    uniqueSessions=len(sessions),
                    heroCtaClicks=sum(1 for event in site_events if event.get("eventType") == "hero_cta_click"),
                    secondaryCtaClicks=sum(1 for event in site_events if event.get("eventType") == "secondary_cta_click"),
                    contactClicks=sum(1 for event in site_events if event.get("eventType") == "contact_click"),
                    ctaClicks=sum(1 for event in site_events if self._is_cta_event(event)),
                    outboundClicks=sum(1 for event in site_events if event.get("eventType") == "outbound_link_click"),
                    calendlyClicks=sum(1 for event in site_events if event.get("eventType") == "calendly_click"),
                    sectionExposures=sum(1 for event in site_events if event.get("eventType") == "section_exposure"),
                    formInteractions=sum(1 for event in site_events if event.get("eventType") == "form_interaction"),
                    messageAttributedVisits=sum(1 for event in site_events if event.get("messageId") or event.get("messageChannel")),
                    timeOnPageSeconds=None,
                    referrers=[{"referrer": ref, "count": count} for ref, count in referrers.most_common(10)],
                    updatedAt=_utc(latest.get("createdAt")) or _now(),
                )
            )
        return results

    async def _lead_metrics(self) -> list[AnalyticsLeadMetrics]:
        events = await self._events()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            lead_id = event.get("leadId")
            if lead_id:
                grouped[str(lead_id)].append(event)
        results: list[AnalyticsLeadMetrics] = []
        for lead_id, lead_events in grouped.items():
            sessions = {event.get("sessionId") for event in lead_events if event.get("sessionId")}
            referrers = Counter(event.get("referrer") for event in lead_events if event.get("referrer"))
            latest = lead_events[0]
            results.append(
                AnalyticsLeadMetrics(
                    leadId=lead_id,
                    siteId=next((str(event.get("siteId")) for event in lead_events if event.get("siteId")), None),
                    themeKey=next((str(event.get("themeKey")) for event in lead_events if event.get("themeKey")), None),
                    visits=sum(1 for event in lead_events if event.get("eventType") == "page_view"),
                    uniqueSessions=len(sessions),
                    heroCtaClicks=sum(1 for event in lead_events if event.get("eventType") == "hero_cta_click"),
                    secondaryCtaClicks=sum(1 for event in lead_events if event.get("eventType") == "secondary_cta_click"),
                    contactClicks=sum(1 for event in lead_events if event.get("eventType") == "contact_click"),
                    ctaClicks=sum(1 for event in lead_events if self._is_cta_event(event)),
                    bookedCalls=sum(1 for event in lead_events if event.get("eventType") == "calendly_click"),
                    outboundClicks=sum(1 for event in lead_events if event.get("eventType") == "outbound_link_click"),
                    formInteractions=sum(1 for event in lead_events if event.get("eventType") == "form_interaction"),
                    messageAttributedVisits=sum(1 for event in lead_events if event.get("messageId") or event.get("messageChannel")),
                    referrers=[{"referrer": ref, "count": count} for ref, count in referrers.most_common(10)],
                    updatedAt=_utc(latest.get("createdAt")) or _now(),
                )
            )
        return results

    async def _variant_metrics(self) -> list[AnalyticsVariantMetrics]:
        events = await self._events()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            variant_key = event.get("variantKey")
            if variant_key:
                grouped[str(variant_key)].append(event)
        results: list[AnalyticsVariantMetrics] = []
        for variant_key, variant_events in grouped.items():
            sessions = {event.get("sessionId") for event in variant_events if event.get("sessionId")}
            latest = variant_events[0]
            results.append(
                AnalyticsVariantMetrics(
                    variantKey=variant_key,
                    themeKey=next((str(event.get("themeKey")) for event in variant_events if event.get("themeKey")), None),
                    siteId=next((str(event.get("siteId")) for event in variant_events if event.get("siteId")), None),
                    leadId=next((str(event.get("leadId")) for event in variant_events if event.get("leadId")), None),
                    pageViews=sum(1 for event in variant_events if event.get("eventType") == "page_view"),
                    uniqueSessions=len(sessions),
                    ctaClicks=sum(1 for event in variant_events if self._is_cta_event(event)),
                    outboundClicks=sum(1 for event in variant_events if event.get("eventType") == "outbound_link_click"),
                    calendlyClicks=sum(1 for event in variant_events if event.get("eventType") == "calendly_click"),
                    updatedAt=_utc(latest.get("createdAt")) or _now(),
                )
            )
        return results

    async def _message_metrics(self) -> list[AnalyticsMessageMetrics]:
        events = await self._events()
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            message_key = self._message_key(event)
            if message_key:
                grouped[message_key].append(event)
        results: list[AnalyticsMessageMetrics] = []
        for _key, message_events in grouped.items():
            latest = message_events[0]
            channel = str(latest.get("messageChannel") or "unknown")
            results.append(
                AnalyticsMessageMetrics(
                    channel=channel,
                    messageId=str(latest.get("messageId")) if latest.get("messageId") else None,
                    leadId=next((str(event.get("leadId")) for event in message_events if event.get("leadId")), None),
                    siteId=next((str(event.get("siteId")) for event in message_events if event.get("siteId")), None),
                    visits=sum(1 for event in message_events if event.get("eventType") == "page_view"),
                    ctaClicks=sum(1 for event in message_events if self._is_cta_event(event)),
                    calendlyClicks=sum(1 for event in message_events if event.get("eventType") == "calendly_click"),
                    outboundClicks=sum(1 for event in message_events if event.get("eventType") == "outbound_link_click"),
                    updatedAt=_utc(latest.get("createdAt")) or _now(),
                )
            )
        return results

    async def get_site_metrics(self, site_id: str) -> AnalyticsSiteMetrics | None:
        events = [event for event in await self._events() if str(event.get("siteId")) == site_id]
        if not events:
            return None
        site_metrics = await self._site_metrics()
        for metrics in site_metrics:
            if metrics.siteId == site_id:
                return metrics
        return None

    async def get_lead_metrics(self, lead_id: str) -> AnalyticsLeadMetrics | None:
        events = [event for event in await self._events() if str(event.get("leadId")) == lead_id]
        if not events:
            return None
        lead_metrics = await self._lead_metrics()
        for metrics in lead_metrics:
            if metrics.leadId == lead_id:
                return metrics
        return None


analytics_repository = AnalyticsRepository()
