from datetime import datetime, timezone

import pytest

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.schemas.lead import LeadUpsertRequest


@pytest.mark.asyncio
async def test_list_pages_returns_page_inventory():
    """Test that list_pages returns page inventory with citations and gaps."""

    # Create a lead on a dedicated domain to avoid collisions with other tests
    req = LeadUpsertRequest(companyName="Test Co", websiteUrl="https://pages.example.com")
    action = await lead_repository.create_lead(req, user_id="test-user")
    lead = action.lead
    lead_id = lead.id

    # Insert an extraction snapshot with page inventory
    now = datetime.now(timezone.utc)
    extraction_doc = {
            "id": "ex-1",
            "leadId": lead_id,
            "jobId": None,
            "version": 1,
            "crawlStatus": "completed",
            "sitemapStatus": "found",
            "pagesDiscovered": 2,
            "pagesCrawled": 2,
            "canonicalWebsiteUrl": lead.websiteUrl,
            "detectedWebsiteUrl": lead.detectedWebsiteUrl,
            "summary": {
                "companyName": lead.companyName,
                "canonicalWebsiteUrl": lead.websiteUrl,
                "detectedWebsiteUrl": lead.detectedWebsiteUrl,
                "positioningSummary": "Test positioning",
                "audienceClues": ["enterprise"],
                "serviceClues": ["consulting"],
                "ctaClues": ["contact"],
                "toneClues": ["professional"],
            },
            "pageInventory": [
                {
                    "url": "https://example.com",
                    "source": "homepage",
                    "status": "crawled",
                    "title": "Test Co - Home",
                    "summary": "Title: Test Co - Home | Description: Leading provider",
                    "depth": 0,
                    "ctaCount": 3,
                    "confidence": 85,
                    "citations": [
                        {
                            "pageUrl": "https://example.com",
                            "evidenceType": "title",
                            "label": "Page title",
                            "excerpt": "Test Co - Home",
                            "confidence": 86,
                        },
                        {
                            "pageUrl": "https://example.com",
                            "evidenceType": "meta",
                            "label": "Meta description",
                            "excerpt": "Leading provider",
                            "confidence": 80,
                        },
                    ],
                    "errors": [],
                },
                {
                    "url": "https://example.com/about",
                    "source": "internal_link",
                    "status": "crawled",
                    "title": "About Us",
                    "summary": "Title: About Us | H1: Our Story",
                    "depth": 1,
                    "ctaCount": 2,
                    "confidence": 78,
                    "citations": [
                        {
                            "pageUrl": "https://example.com/about",
                            "evidenceType": "title",
                            "label": "Page title",
                            "excerpt": "About Us",
                            "confidence": 82,
                        },
                    ],
                    "errors": ["summary_sparse"],
                },
            ],
            "sourceCitations": [],
            "brandAssetCues": [],
            "sitemapUrls": [],
            "confidenceScore": 82,
            "gapItems": ["summary_sparse"],
            "errors": [],
            "createdAt": now,
            "updatedAt": now,
        }
    database = get_database()
    await database["site_extractions"].insert_one(extraction_doc)

    # Test list_pages
    pages_response = await lead_repository.list_pages(lead_id)
    assert pages_response is not None
    assert pages_response.leadId == lead_id
    assert pages_response.extractionId == "ex-1"
    assert pages_response.crawlStatus == "completed"
    assert pages_response.pagesDiscovered == 2
    assert pages_response.pagesCrawled == 2
    assert len(pages_response.pages) == 2

    # Verify page details
    page1 = pages_response.pages[0]
    assert page1.url == "https://example.com"
    assert page1.title == "Test Co - Home"
    assert page1.status == "crawled"
    assert page1.confidence == 85
    assert len(page1.citations) == 2
    assert page1.citations[0].evidenceType == "title"

    page2 = pages_response.pages[1]
    assert page2.url == "https://example.com/about"
    assert page2.title == "About Us"
    assert len(page2.errors) == 1
    assert page2.errors[0] == "summary_sparse"

    # Verify gap items
    assert "summary_sparse" in pages_response.gapItems


@pytest.mark.asyncio
async def test_list_pages_returns_empty_for_no_extraction():
    """Test that list_pages returns empty state when no extraction exists."""

    # Create a lead without extraction
    req = LeadUpsertRequest(companyName="Test Co 2", websiteUrl="https://example2.com")
    action = await lead_repository.create_lead(req, user_id="test-user")
    lead = action.lead
    lead_id = lead.id

    # Test list_pages with no extraction
    pages_response = await lead_repository.list_pages(lead_id)
    assert pages_response is not None
    assert pages_response.leadId == lead_id
    assert pages_response.extractionId is None
    assert pages_response.crawlStatus == "idle"
    assert pages_response.pagesDiscovered == 0
    assert pages_response.pagesCrawled == 0
    assert len(pages_response.pages) == 0
    assert "crawl_not_started" in pages_response.gapItems


@pytest.mark.asyncio
async def test_approve_brief_blocked_by_critical_gaps():
    """Test that brief approval is blocked when critical extraction gaps exist."""

    # Create a lead
    req = LeadUpsertRequest(companyName="Test Co 3", websiteUrl="https://example3.com")
    action = await lead_repository.create_lead(req, user_id="test-user")
    lead = action.lead
    lead_id = lead.id

    # Insert an extraction snapshot with critical gaps
    now = datetime.now(timezone.utc)
    extraction_doc = {
            "id": "ex-2",
            "leadId": lead_id,
            "jobId": None,
            "version": 1,
            "crawlStatus": "failed",
            "sitemapStatus": "missing",
            "pagesDiscovered": 0,
            "pagesCrawled": 0,
            "canonicalWebsiteUrl": lead.websiteUrl,
            "detectedWebsiteUrl": lead.detectedWebsiteUrl,
            "summary": {
                "companyName": lead.companyName,
                "canonicalWebsiteUrl": lead.websiteUrl,
                "detectedWebsiteUrl": lead.detectedWebsiteUrl,
                "positioningSummary": None,
                "audienceClues": [],
                "serviceClues": [],
                "ctaClues": [],
                "toneClues": [],
            },
            "pageInventory": [],
            "sourceCitations": [],
            "brandAssetCues": [],
            "sitemapUrls": [],
            "confidenceScore": 0,
            "gapItems": ["homepage_unreachable", "low_confidence_extraction"],
            "errors": ["crawl_failed"],
            "createdAt": now,
            "updatedAt": now,
        }
    database = get_database()
    await database["site_extractions"].insert_one(extraction_doc)

    # Create a brief
    brief = await lead_repository.create_brief(lead_id)
    assert brief is not None

    # Attempt to approve brief with critical gaps should raise ValueError
    try:
        await lead_repository.approve_brief(lead_id, approved_by="tester")
        assert False, "Expected ValueError for critical gaps"
    except ValueError as exc:
        assert str(exc) == "brief_requires_critical_gaps_resolved"


@pytest.mark.asyncio
async def test_approve_brief_succeeds_without_critical_gaps():
    """Test that brief approval succeeds when no critical gaps exist."""

    # Create a lead
    req = LeadUpsertRequest(companyName="Test Co 4", websiteUrl="https://example4.com")
    action = await lead_repository.create_lead(req, user_id="test-user")
    lead = action.lead
    lead_id = lead.id

    # Insert an extraction snapshot with non-critical gaps only
    now = datetime.now(timezone.utc)
    extraction_doc = {
        "id": "ex-3",
        "leadId": lead_id,
        "jobId": None,
        "version": 1,
        "crawlStatus": "completed",
        "sitemapStatus": "found",
        "pagesDiscovered": 1,
        "pagesCrawled": 1,
        "canonicalWebsiteUrl": lead.websiteUrl,
        "detectedWebsiteUrl": lead.detectedWebsiteUrl,
        "summary": {
            "companyName": lead.companyName,
            "canonicalWebsiteUrl": lead.websiteUrl,
            "detectedWebsiteUrl": lead.detectedWebsiteUrl,
            "positioningSummary": "Test positioning",
            "audienceClues": [],
            "serviceClues": [],
            "ctaClues": [],
            "toneClues": [],
        },
        "pageInventory": [
            {
                "url": "https://example4.com",
                "source": "homepage",
                "status": "crawled",
                "title": "Test Co 4 - Home",
                "summary": "Title: Test Co 4 - Home",
                "depth": 0,
                "ctaCount": 1,
                "confidence": 75,
                "citations": [],
                "errors": [],
            },
        ],
        "sourceCitations": [],
        "brandAssetCues": [],
        "sitemapUrls": [],
        "confidenceScore": 75,
        "gapItems": ["sitemap_unavailable"],  # Non-critical gap
        "errors": [],
        "createdAt": now,
        "updatedAt": now,
    }
    database = get_database()
    await database["site_extractions"].insert_one(extraction_doc)

    # Create a brief
    brief = await lead_repository.create_brief(lead_id)
    assert brief is not None

    # Approve brief should succeed with non-critical gaps
    approved_brief = await lead_repository.approve_brief(lead_id, approved_by="tester")
    assert approved_brief is not None
    assert approved_brief.approvalState == "approved"
    assert approved_brief.approvedBy == "tester"
    assert approved_brief.approvedAt is not None
