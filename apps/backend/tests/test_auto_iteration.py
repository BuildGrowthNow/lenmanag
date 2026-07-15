from datetime import datetime, timezone
from typing import Any

import pytest
from unittest.mock import AsyncMock, patch

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import site_repository
from app.schemas.lead import LeadUpsertRequest


@pytest.mark.asyncio
async def test_automatic_second_pass_visual_redesign_iteration():
    """Automatic second-pass iteration applies refined premium components without manual refinement flags."""

    async def run_test() -> None:
        # Create lead and minimal extraction snapshot
        req = LeadUpsertRequest(companyName="Iter Co", websiteUrl="https://iter.example.com")
        action = await lead_repository.create_lead(req)
        lead = action.lead
        site_id = lead.id

        now = datetime.now(timezone.utc)
        extraction_doc = {
            "id": "ex-iter",
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
                "positioningSummary": "Iter positioning",
                "audienceClues": [],
                "serviceClues": [],
                "ctaClues": [],
                "toneClues": [],
            },
            "pageInventory": [],
            "sourceCitations": [],
            "brandAssetCues": [],
            "assetManifest": [],
            "sectionInventory": [],
            "visualCaptureSummary": {},
            "sitemapUrls": [],
            "confidenceScore": 80,
            "gapItems": [],
            "errors": [],
            "crawlBudgetUsed": 0,
            "crawlBudgetLimit": 3_000_000,
            "crawlTimeElapsedSeconds": 1,
            "assetCacheStats": {},
            "assetRetentionDays": 7,
            "createdAt": now,
            "updatedAt": now,
        }
        database = get_database()
        await database["site_extractions"].insert_one(extraction_doc)

        # Create and approve a brief so generation is allowed
        brief = await lead_repository.create_brief(site_id)
        assert brief is not None
        await lead_repository.approve_brief(site_id, approved_by="tester")

        # Mock visual redesign brief generation to produce baseline components
        initial_redesign = [
            {
                "pageUrl": lead.websiteUrl,
                "critiques": [
                    {
                        "sectionType": "services",
                        "contentToReuse": ["Our services"],
                        "recommendedComponent": "services-grid",
                        "redesignGoal": "Improve services layout",
                        "visualDirection": "Premium services grid",
                        "confidence": 80,
                    },
                    {
                        "sectionType": "proof",
                        "contentToReuse": ["Customer proof"],
                        "recommendedComponent": "proof-grid",
                        "redesignGoal": "Highlight proof points",
                        "visualDirection": "Premium proof grid",
                        "confidence": 80,
                    },
                ],
                "artDirection": "neutral",
            }
        ]

        async def fake_generate_redesign(*_args: Any, **_kwargs: Any):  # pragma: no cover
            return initial_redesign

        # Two screenshot QA passes: first below threshold with critique, second above
        screenshot_results = [
            {
                "success": True,
                "desktopScreenshotUrl": "screenshots/iter/v1-desktop.png",
                "mobileScreenshotUrl": "screenshots/iter/v1-mobile.png",
                "layoutHash": "layout-hash-v1",
                "qualityScore": 70,
                "sectionScores": [],
                "rawCritique": "INTERNAL QA: needs better layout",
                "readinessAssessment": "needs_refinement",
                "passThreshold": False,
                "capturedAt": "2024-06-01T12:00:00Z",
            },
            {
                "success": True,
                "desktopScreenshotUrl": "screenshots/iter/v2-desktop.png",
                "mobileScreenshotUrl": "screenshots/iter/v2-mobile.png",
                "layoutHash": "layout-hash-v2",
                "qualityScore": 92,
                "sectionScores": [],
                "rawCritique": "Looks premium now",
                "readinessAssessment": "production_ready",
                "passThreshold": True,
                "capturedAt": "2024-06-01T12:10:00Z",
            },
        ]

        comparator = site_repository._screenshot_comparator  # type: ignore[attr-defined]
        comparator.compare_layout_screenshot = AsyncMock(side_effect=screenshot_results)  # type: ignore[assignment]

        improvement_payload = {
            "overallApproach": "Editorial premium layout with clear hierarchy.",
            "sectionImprovements": [
                {
                    "sectionTitle": "Services",
                    "currentIssues": ["Layout too list-like"],
                    "recommendedChanges": ["Use premium services bento layout"],
                    "priority": "high",
                },
                {
                    "sectionTitle": "Proof",
                    "currentIssues": ["Testimonials lack structure"],
                    "recommendedChanges": ["Use carousel for proof"],
                    "priority": "medium",
                },
            ],
            "estimatedNewScore": 90,
            "implementationNotes": "Switch to premium components for key sections.",
        }

        mock_analyzer = AsyncMock()
        mock_analyzer.generate_improvement_brief = AsyncMock(return_value=improvement_payload)

        with (
            patch(
                "app.core.visual_redesign.generate_visual_redesign_brief",
                side_effect=fake_generate_redesign,
            ),
            patch(
                "app.core.screenshot_analyzer.get_screenshot_analyzer",
                return_value=mock_analyzer,
            ),
        ):
            # First generation run: attaches improvementRecommendations
            site_v1 = await site_repository.generate_site(site_id)
            assert site_v1 is not None
            assert site_v1.version == 1
            assert site_v1.improvementRecommendations is not None
            assert site_v1.screenshotRefs
            assert site_v1.screenshotRefs[0].contentHash == "layout-hash-v1"
            assert site_v1.isManuallyRefined is False
            assert not site_v1.promptHistory

            # Second generation run: should apply automatic refinement based on improvementRecommendations
            site_v2 = await site_repository.generate_site(site_id)
            assert site_v2 is not None
            assert site_v2.version == 2
            assert site_v2.qualityScore >= 90
            assert site_v2.screenshotRefs
            assert site_v2.screenshotRefs[0].contentHash == "layout-hash-v2"

            # Automatic iteration path must not mark site as manually refined or touch prompt history
            assert site_v2.isManuallyRefined is False
            assert site_v2.refinementPromptId is None
            assert not site_v2.promptHistory

            # Section stack should now use refined premium components for services and proof
            kinds_to_components = {
                s.kind: s.componentId for s in site_v2.sectionStack
            }
            assert kinds_to_components.get("services") == "services-bento"
            assert kinds_to_components.get("proof") == "proof-carousel"

            # Raw QA critique text must not leak into public copy
            public_text_fields = []
            if site_v2.heroVariant:
                public_text_fields.extend(
                    [
                        site_v2.heroVariant.headline,
                        site_v2.heroVariant.subheadline,
                        site_v2.heroVariant.supportingLine,
                    ]
                )
            for section in site_v2.sectionStack:
                public_text_fields.append(section.headline or "")
                public_text_fields.append(section.body or "")
                public_text_fields.extend(section.items or [])

            joined = "\n".join(t or "" for t in public_text_fields)
            assert "INTERNAL QA" not in joined

    await run_test()
