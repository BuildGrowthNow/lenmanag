from datetime import datetime, timezone
import asyncio

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import site_repository, THEME_LIBRARY
from app.schemas.lead import LeadUpsertRequest
from app.schemas.site import SiteOverrideCreateRequest


def test_operator_theme_override_applied():
    async def run_test():
        # Create a lead on a distinct domain to avoid cross-test collisions
        req = LeadUpsertRequest(companyName="Test Co", websiteUrl="https://override.example.com")
        action = await lead_repository.create_lead(req)
        lead = action.lead
        site_id = lead.id

        # Insert a minimal extraction snapshot into in-memory store
        now = datetime.now(timezone.utc)
        extraction_doc = {
            "id": "ex-1",
            "leadId": site_id,
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
            "confidenceScore": 80,
            "gapItems": [],
            "errors": [],
            "createdAt": now,
            "updatedAt": now,
        }
        database = get_database()
        await database["site_extractions"].insert_one(extraction_doc)

        # Create and approve a brief so generation is allowed
        brief = await lead_repository.create_brief(site_id)
        assert brief is not None
        await lead_repository.approve_brief(site_id, approved_by="tester")

        # First generation to create the site document
        site_before = await site_repository.generate_site(site_id)
        assert site_before is not None

        # Apply operator override for themeKey
        override_req = SiteOverrideCreateRequest(scope="brand", path="themeKey", value="signal-panel", reason="Operator selected theme")
        created = await site_repository.create_override(site_id, override_req)
        assert created is not None

        # Regenerate site and assert override is honored
        site = await site_repository.generate_site(site_id)
        assert site is not None
        assert site.themeKey == "signal-panel"
        assert "Operator selected theme" in site.themeRationale

        # Verify brand tokens reflect the selected theme
        theme = next(t for t in THEME_LIBRARY if t["themeKey"] == "signal-panel")
        assert site.brandTokens.typography.value == theme["typographyPairing"]

        # Overrides persisted and overrideCount updated
        assert site.overrideCount >= 1
        assert any(o.path == "themeKey" and o.value == "signal-panel" for o in site.overrides)

        # Disable override and ensure it is removed from subsequent generations
        disabled = await site_repository.disable_override(site_id, created.id)
        assert disabled is not None
        assert disabled.status == "disabled"

        site_after_disable = await site_repository.generate_site(site_id)
        assert site_after_disable is not None
        assert site_after_disable.overrideCount == 0
        assert all(o.status == "active" for o in site_after_disable.overrides)
        assert all(o.path != "themeKey" for o in site_after_disable.overrides)

    asyncio.run(run_test())
