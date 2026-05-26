from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

AnalyticsEventType = Literal[
    "page_view",
    "hero_cta_click",
    "secondary_cta_click",
    "contact_click",
    "calendly_click",
    "section_exposure",
    "form_interaction",
    "outbound_link_click",
    "admin_action",
    "lead_created",
    "lead_imported",
    "site_generated",
    "site_republished",
    "site_override_applied",
    "site_export_created",
    "message_draft_edited",
    "message_marked_ready",
    "site_opened",
    "brief_approved",
    "brief_edited",
    "theme_variant_changed",
    "generation_regenerated",
]


class AnalyticsEvent(BaseModel):
    id: str
    siteId: Optional[str] = None
    leadId: Optional[str] = None
    sessionId: Optional[str] = None
    visitorFingerprint: Optional[str] = None
    themeKey: Optional[str] = None
    variantKey: Optional[str] = None
    messageId: Optional[str] = None
    messageChannel: Optional[str] = None
    eventType: str
    eventName: str
    pagePath: Optional[str] = None
    referrer: Optional[str] = None
    utm: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime


class AnalyticsEventCreateRequest(BaseModel):
    siteId: Optional[str] = None
    leadId: Optional[str] = None
    sessionId: Optional[str] = None
    visitorFingerprint: Optional[str] = None
    themeKey: Optional[str] = None
    variantKey: Optional[str] = None
    messageId: Optional[str] = None
    messageChannel: Optional[str] = None
    eventType: AnalyticsEventType
    eventName: str
    pagePath: Optional[str] = None
    referrer: Optional[str] = None
    utm: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnalyticsSummary(BaseModel):
    totalEvents: int
    totalPageViews: int
    totalCTAClicks: int
    totalOutboundClicks: int
    totalCalendlyClicks: int
    totalSectionExposures: int
    totalFormInteractions: int
    uniqueSessions: int
    totalSites: int
    totalLeads: int
    eventsByType: dict[str, int] = Field(default_factory=dict)
    topPages: list[dict[str, Any]] = Field(default_factory=list)
    topSources: list[dict[str, Any]] = Field(default_factory=list)
    referrers: list[dict[str, Any]] = Field(default_factory=list)
    messageAttribution: list[dict[str, Any]] = Field(default_factory=list)
    updatedAt: datetime


class AnalyticsSiteMetrics(BaseModel):
    siteId: str
    leadId: Optional[str] = None
    themeKey: Optional[str] = None
    variantKey: Optional[str] = None
    pageViews: int
    uniqueSessions: int
    heroCtaClicks: int
    secondaryCtaClicks: int
    contactClicks: int
    ctaClicks: int
    outboundClicks: int
    calendlyClicks: int
    sectionExposures: int
    formInteractions: int
    messageAttributedVisits: int
    timeOnPageSeconds: Optional[float] = None
    referrers: list[dict[str, Any]] = Field(default_factory=list)
    updatedAt: datetime


class AnalyticsLeadMetrics(BaseModel):
    leadId: str
    siteId: Optional[str] = None
    themeKey: Optional[str] = None
    visits: int
    uniqueSessions: int
    heroCtaClicks: int
    secondaryCtaClicks: int
    contactClicks: int
    ctaClicks: int
    bookedCalls: int
    outboundClicks: int
    formInteractions: int
    messageAttributedVisits: int
    referrers: list[dict[str, Any]] = Field(default_factory=list)
    updatedAt: datetime


class AnalyticsVariantMetrics(BaseModel):
    variantKey: str
    themeKey: Optional[str] = None
    siteId: Optional[str] = None
    leadId: Optional[str] = None
    pageViews: int
    uniqueSessions: int
    ctaClicks: int
    outboundClicks: int
    calendlyClicks: int
    updatedAt: datetime


class AnalyticsMessageMetrics(BaseModel):
    channel: str
    messageId: Optional[str] = None
    leadId: Optional[str] = None
    siteId: Optional[str] = None
    visits: int
    ctaClicks: int
    calendlyClicks: int
    outboundClicks: int
    updatedAt: datetime


class AnalyticsDashboardResponse(BaseModel):
    summary: AnalyticsSummary
    siteMetrics: list[AnalyticsSiteMetrics] = Field(default_factory=list)
    leadMetrics: list[AnalyticsLeadMetrics] = Field(default_factory=list)
    variantMetrics: list[AnalyticsVariantMetrics] = Field(default_factory=list)
    messageMetrics: list[AnalyticsMessageMetrics] = Field(default_factory=list)
