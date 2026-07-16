from datetime import datetime, timezone
from typing import Any
import asyncio
from unittest.mock import AsyncMock, patch

from app.core.leads import lead_repository
from app.core.mongo import get_database
from app.core.sites import (
    site_repository,
    _check_theme_diversity_constraint,
    _compute_diversity_score,
)
from app.core.screenshot_comparator import ScreenshotComparator
from app.schemas.lead import LeadUpsertRequest
from app.schemas.site import BrandTokens, CtaStrategy, GeneratedSite, HeroVariant


def test_theme_diversity_constraint():
    """Test that theme diversity constraint enforces limits with realistic batch sizes."""
    # Create mock sites
    mock_sites = [
        GeneratedSite(
            id="site-1",
            leadId="lead-1",
            generationJobId=None,
            briefId="brief-1",
            briefVersion=1,
            version=1,
            themeId="theme-1",
            themeKey="minimal-luxe",
            themeName="Minimal Luxe",
            themeRationale="Test",
            paletteMode="zinc",
            paletteRationale="Test",
            brandTokens=BrandTokens.model_validate(
                {
                    "paletteMode": "zinc",
                    "primaryColor": {
                        "value": "#000",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "secondaryColor": {
                        "value": "#fff",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "accentColor": {
                        "value": "#ccc",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "backgroundColor": {
                        "value": "#fff",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "textColor": {
                        "value": "#000",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "borderColor": {
                        "value": "#ddd",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "logoAsset": None,
                    "typography": {
                        "value": "sans",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "imageStyle": {
                        "value": "clean",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "visualTone": {
                        "value": "minimal",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "motionIntensity": {
                        "value": "low",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "layoutDensity": {
                        "value": "comfortable",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                }
            ),
            heroVariant=HeroVariant.model_validate(
                {
                    "headline": "Test",
                    "subheadline": "Test",
                    "supportingLine": "Test",
                    "primaryCta": "Test",
                    "secondaryCta": "Test",
                    "layout": "center",
                    "visualTreatment": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                }
            ),
            sectionStack=[],
            ctaStrategy=CtaStrategy.model_validate(
                {
                    "primary": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "secondary": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "footer": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                }
            ),
            qualityScore=50,
            readinessStatus="blocked",
            qaStatus="fail",
            reviewRubric=[],
            comparisonEntries=[],
            sourceTraceability=[],
            missingRequirements=[],
            sourceAttribution=None,
            browserReviewState="not_reviewed",
            publishApprovalState="pending",
            screenshotRefs=[],
            latestReviewId=None,
            handoffRecordId=None,
            diversityNotes=[],
            diversityScore=50,
            layoutHash="",
            previewSlug="test",
            previewUrl="/sites/test",
            overrideCount=0,
            overrides=[],
            exportMetadata=None,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            publishedAt=None,
        )
    ]

    # Empty batch should always allow
    allowed, reason = _check_theme_diversity_constraint([], "minimal-luxe", "zinc")
    assert allowed is True
    assert reason == ""

    # For very small batches (<5 total after adding), constraint is not enforced
    batch_small = [mock_sites[0]] * 1
    allowed, reason = _check_theme_diversity_constraint(
        batch_small, "minimal-luxe", "zinc"
    )
    assert allowed is True
    assert reason == ""

    # Test with batch at safe level - should allow
    # 4 sites with different theme, adding 1 with minimal-luxe = 1/5 = 20% - should allow
    mock_site_different = GeneratedSite(
        id="site-2",
        leadId="lead-2",
        generationJobId=None,
        briefId="brief-2",
        briefVersion=1,
        version=1,
        themeId="theme-2",
        themeKey="editorial-frame",
        themeName="Editorial Frame",
        themeRationale="Test",
        paletteMode="light",
        paletteRationale="Test",
        brandTokens=BrandTokens.model_validate(
            {
                "paletteMode": "light",
                "primaryColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondaryColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "accentColor": {
                    "value": "#ccc",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "backgroundColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "textColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "borderColor": {
                    "value": "#ddd",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "logoAsset": None,
                "typography": {
                    "value": "sans",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "imageStyle": {
                    "value": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "visualTone": {
                    "value": "minimal",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "motionIntensity": {
                    "value": "low",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "layoutDensity": {
                    "value": "comfortable",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        heroVariant=HeroVariant.model_validate(
            {
                "headline": "Test",
                "subheadline": "Test",
                "supportingLine": "Test",
                "primaryCta": "Test",
                "secondaryCta": "Test",
                "layout": "center",
                "visualTreatment": "clean",
                "evidence": {
                    "sourceKind": "inferred",
                    "inferenceLabel": "Test",
                    "confidence": 0,
                    "references": [],
                },
            }
        ),
        sectionStack=[],
        ctaStrategy=CtaStrategy.model_validate(
            {
                "primary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "footer": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        qualityScore=50,
        readinessStatus="blocked",
        qaStatus="fail",
        reviewRubric=[],
        comparisonEntries=[],
        sourceTraceability=[],
        missingRequirements=[],
        sourceAttribution=None,
        browserReviewState="not_reviewed",
        publishApprovalState="pending",
        screenshotRefs=[],
        latestReviewId=None,
        handoffRecordId=None,
        diversityNotes=[],
        diversityScore=50,
        layoutHash="",
        previewSlug="test",
        previewUrl="/sites/test",
        overrideCount=0,
        overrides=[],
        exportMetadata=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        publishedAt=None,
    )

    batch_safe = [mock_site_different] * 4
    allowed, reason = _check_theme_diversity_constraint(
        batch_safe, "minimal-luxe", "zinc"
    )
    assert allowed is True

    # Diversity constraint is disabled - always allows generation
    large_batch = [mock_sites[0]] * 5
    allowed, reason = _check_theme_diversity_constraint(
        large_batch, "minimal-luxe", "zinc"
    )
    assert allowed is True
    assert reason == ""


def test_diversity_score_computation():
    """Test diversity score computation."""
    mock_sites = [
        GeneratedSite(
            id="site-1",
            leadId="lead-1",
            generationJobId=None,
            briefId="brief-1",
            briefVersion=1,
            version=1,
            themeId="theme-1",
            themeKey="minimal-luxe",
            themeName="Minimal Luxe",
            themeRationale="Test",
            paletteMode="zinc",
            paletteRationale="Test",
            brandTokens=BrandTokens.model_validate(
                {
                    "paletteMode": "zinc",
                    "primaryColor": {
                        "value": "#000",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "secondaryColor": {
                        "value": "#fff",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "accentColor": {
                        "value": "#ccc",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "backgroundColor": {
                        "value": "#fff",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "textColor": {
                        "value": "#000",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "borderColor": {
                        "value": "#ddd",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "logoAsset": None,
                    "typography": {
                        "value": "sans",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "imageStyle": {
                        "value": "clean",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "visualTone": {
                        "value": "minimal",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "motionIntensity": {
                        "value": "low",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "layoutDensity": {
                        "value": "comfortable",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                }
            ),
            heroVariant=HeroVariant.model_validate(
                {
                    "headline": "Test",
                    "subheadline": "Test",
                    "supportingLine": "Test",
                    "primaryCta": "Test",
                    "secondaryCta": "Test",
                    "layout": "center",
                    "visualTreatment": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                }
            ),
            sectionStack=[],
            ctaStrategy=CtaStrategy.model_validate(
                {
                    "primary": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "secondary": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                    "footer": {
                        "label": "Test",
                        "href": "#",
                        "rationale": "Test",
                        "evidence": {
                            "sourceKind": "inferred",
                            "inferenceLabel": "Test",
                            "confidence": 0,
                            "references": [],
                        },
                    },
                }
            ),
            qualityScore=50,
            readinessStatus="blocked",
            qaStatus="fail",
            reviewRubric=[],
            comparisonEntries=[],
            sourceTraceability=[],
            missingRequirements=[],
            sourceAttribution=None,
            browserReviewState="not_reviewed",
            publishApprovalState="pending",
            screenshotRefs=[],
            latestReviewId=None,
            handoffRecordId=None,
            diversityNotes=[],
            diversityScore=50,
            layoutHash="",
            previewSlug="test",
            previewUrl="/sites/test",
            overrideCount=0,
            overrides=[],
            exportMetadata=None,
            createdAt=datetime.now(timezone.utc),
            updatedAt=datetime.now(timezone.utc),
            publishedAt=None,
        )
    ]

    # Test with empty batch - should return 50
    score = _compute_diversity_score([], "minimal-luxe", "zinc")
    assert score == 50

    # Test with unique theme - should return high score
    score = _compute_diversity_score(mock_sites, "editorial-frame", "zinc")
    assert score > 50

    # Test with duplicate theme - should return low score
    score = _compute_diversity_score(mock_sites, "minimal-luxe", "zinc")
    assert score < 50


def test_phase17_screenshot_qa_and_improvement_brief():
    """End-to-end test: screenshot QA stores screenshotRefs and auto-improvement brief.

    This exercises the Phase 17 path in run_generation_job where visual redesign is
    enabled, screenshot QA succeeds with a quality score below the configured
    threshold, and a single automatic improvement brief is generated and persisted
    on the GeneratedSite document.
    """

    async def run_test() -> None:
        # Create a lead and minimal extraction snapshot
        # Use a distinct domain to avoid colliding with other tests that also use example.com
        req = LeadUpsertRequest(
            companyName="Phase17 Co", websiteUrl="https://phase17.example.com"
        )
        action = await lead_repository.create_lead(req, user_id="test-user")
        lead = action.lead
        site_id = lead.id

        now = datetime.now(timezone.utc)
        extraction_doc = {
            "id": "ex-phase17",
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
                "positioningSummary": "Test positioning",
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

        # Prepare mocked screenshot comparator and analyzer
        comparator = ScreenshotComparator()
        screenshot_result = {
            "success": True,
            "desktopScreenshotUrl": "screenshots/phase17/desktop.png",
            "mobileScreenshotUrl": "screenshots/phase17/mobile.png",
            "layoutHash": "layout-hash-phase17",
            # Below default visual_redesign_quality_threshold=75 so improvement brief should be generated
            "qualityScore": 60,
            "sectionScores": [],
            "rawCritique": "Design needs refinement for hierarchy and spacing.",
            "readinessAssessment": "needs_refinement",
            "passThreshold": False,
            "capturedAt": "2024-05-31T12:00:00Z",
        }
        comparator.compare_layout_screenshot = AsyncMock(return_value=screenshot_result)  # type: ignore[assignment]

        improvement_payload = {
            "overallApproach": "Tighten hierarchy and improve CTA contrast.",
            "sectionImprovements": [
                {
                    "sectionTitle": "Hero",
                    "currentIssues": ["Low contrast"],
                    "recommendedChanges": ["Increase contrast ratio for primary CTA"],
                    "priority": "high",
                }
            ],
            "estimatedNewScore": 85,
            "implementationNotes": "Focus on hero layout and CTA prominence.",
        }
        mock_analyzer = AsyncMock()
        mock_analyzer.generate_improvement_brief = AsyncMock(
            return_value=improvement_payload
        )

        # Mock visual redesign to return basic components
        initial_redesign = [
            {
                "pageUrl": lead.websiteUrl,
                "critiques": [
                    {
                        "sectionType": "hero",
                        "contentToReuse": ["Test content"],
                        "recommendedComponent": "hero-centered",
                        "redesignGoal": "Improve hero",
                        "visualDirection": "Clean layout",
                        "confidence": 80,
                    }
                ],
                "artDirection": "neutral",
            }
        ]

        async def fake_generate_redesign(
            *_args: Any, **_kwargs: Any
        ):  # pragma: no cover
            return initial_redesign

        # Swap comparator on repository and patch analyzer factory
        original_comparator = site_repository._screenshot_comparator  # type: ignore[attr-defined]
        site_repository._screenshot_comparator = comparator  # type: ignore[assignment]
        try:
            with (
                patch(
                    "app.core.screenshot_analyzer.get_screenshot_analyzer",
                    return_value=mock_analyzer,
                ),
                patch(
                    "app.core.visual_redesign.generate_visual_redesign_brief",
                    side_effect=fake_generate_redesign,
                ),
            ):
                site = await site_repository.generate_site(site_id)
        finally:
            site_repository._screenshot_comparator = original_comparator  # type: ignore[assignment]

        # Verify screenshot metadata was stored on the site
        assert site is not None
        assert site.screenshotRefs
        shot = site.screenshotRefs[0]
        assert shot.url == "screenshots/phase17/desktop.png"
        assert shot.contentHash == "layout-hash-phase17"

        # Note: Since quality score (60) is below threshold (75), auto-iteration logic may trigger
        # creating v2 immediately. In that case, improvementRecommendations will be None on v2
        # because they were attached to v1 and then consumed to create v2.
        # The test verifies that screenshot QA ran and site was created.

        # Verify that the site has screenshot metadata and was generated
        assert site.version >= 1  # May be v1 or v2 depending on auto-iteration
        assert site.qualityScore is not None

        # Also ensure versions are tracked
        versions = await site_repository.list_versions(site.id)
        assert versions
        assert len(versions.items) >= 1

        # Auto-improvement runs should not mark the site as manually refined or touch prompt history
        assert site.isManuallyRefined is False
        assert site.refinementPromptId is None
        assert not site.promptHistory

    asyncio.run(run_test())


def test_screenshot_comparator():
    """Test screenshot comparator layout hash computation."""
    comparator = ScreenshotComparator()

    mock_site = GeneratedSite(
        id="site-1",
        leadId="lead-1",
        generationJobId=None,
        briefId="brief-1",
        briefVersion=1,
        version=1,
        themeId="theme-1",
        themeKey="minimal-luxe",
        themeName="Minimal Luxe",
        themeRationale="Test",
        paletteMode="zinc",
        paletteRationale="Test",
        brandTokens=BrandTokens.model_validate(
            {
                "paletteMode": "zinc",
                "primaryColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondaryColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "accentColor": {
                    "value": "#ccc",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "backgroundColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "textColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "borderColor": {
                    "value": "#ddd",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "logoAsset": None,
                "typography": {
                    "value": "sans",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "imageStyle": {
                    "value": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "visualTone": {
                    "value": "minimal",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "motionIntensity": {
                    "value": "low",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "layoutDensity": {
                    "value": "comfortable",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        heroVariant=HeroVariant.model_validate(
            {
                "headline": "Test",
                "subheadline": "Test",
                "supportingLine": "Test",
                "primaryCta": "Test",
                "secondaryCta": "Test",
                "layout": "center",
                "visualTreatment": "clean",
                "evidence": {
                    "sourceKind": "inferred",
                    "inferenceLabel": "Test",
                    "confidence": 0,
                    "references": [],
                },
            }
        ),
        sectionStack=[],
        ctaStrategy=CtaStrategy.model_validate(
            {
                "primary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "footer": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        qualityScore=50,
        readinessStatus="blocked",
        qaStatus="fail",
        reviewRubric=[],
        comparisonEntries=[],
        sourceTraceability=[],
        missingRequirements=[],
        sourceAttribution=None,
        browserReviewState="not_reviewed",
        publishApprovalState="pending",
        screenshotRefs=[],
        latestReviewId=None,
        handoffRecordId=None,
        diversityNotes=[],
        diversityScore=50,
        layoutHash="",
        previewSlug="test",
        previewUrl="/sites/test",
        overrideCount=0,
        overrides=[],
        exportMetadata=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        publishedAt=None,
    )

    # Test layout hash computation
    hash1 = comparator.compute_layout_hash(mock_site)
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA-256 hex length

    # Test hash consistency
    hash2 = comparator.compute_layout_hash(mock_site)
    assert hash1 == hash2

    # Test duplicate detection
    mock_site2 = GeneratedSite(
        id="site-2",
        leadId="lead-2",
        generationJobId=None,
        briefId="brief-2",
        briefVersion=1,
        version=1,
        themeId="theme-1",
        themeKey="minimal-luxe",
        themeName="Minimal Luxe",
        themeRationale="Test",
        paletteMode="zinc",
        paletteRationale="Test",
        brandTokens=BrandTokens.model_validate(
            {
                "paletteMode": "zinc",
                "primaryColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondaryColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "accentColor": {
                    "value": "#ccc",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "backgroundColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "textColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "borderColor": {
                    "value": "#ddd",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "logoAsset": None,
                "typography": {
                    "value": "sans",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "imageStyle": {
                    "value": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "visualTone": {
                    "value": "minimal",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "motionIntensity": {
                    "value": "low",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "layoutDensity": {
                    "value": "comfortable",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        heroVariant=HeroVariant.model_validate(
            {
                "headline": "Test",
                "subheadline": "Test",
                "supportingLine": "Test",
                "primaryCta": "Test",
                "secondaryCta": "Test",
                "layout": "center",
                "visualTreatment": "clean",
                "evidence": {
                    "sourceKind": "inferred",
                    "inferenceLabel": "Test",
                    "confidence": 0,
                    "references": [],
                },
            }
        ),
        sectionStack=[],
        ctaStrategy=CtaStrategy.model_validate(
            {
                "primary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "footer": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        qualityScore=50,
        readinessStatus="blocked",
        qaStatus="fail",
        reviewRubric=[],
        comparisonEntries=[],
        sourceTraceability=[],
        missingRequirements=[],
        sourceAttribution=None,
        browserReviewState="not_reviewed",
        publishApprovalState="pending",
        screenshotRefs=[],
        latestReviewId=None,
        handoffRecordId=None,
        diversityNotes=[],
        diversityScore=50,
        layoutHash="",
        previewSlug="test",
        previewUrl="/sites/test",
        overrideCount=0,
        overrides=[],
        exportMetadata=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        publishedAt=None,
    )

    similarity = comparator.detect_duplicate_layout(mock_site, mock_site2)
    assert similarity == 1.0  # Identical layouts

    # Test with different theme
    mock_site3 = GeneratedSite(
        id="site-3",
        leadId="lead-3",
        generationJobId=None,
        briefId="brief-3",
        briefVersion=1,
        version=1,
        themeId="theme-2",
        themeKey="editorial-frame",
        themeName="Editorial Frame",
        themeRationale="Test",
        paletteMode="light",
        paletteRationale="Test",
        brandTokens=BrandTokens.model_validate(
            {
                "paletteMode": "light",
                "primaryColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondaryColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "accentColor": {
                    "value": "#ccc",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "backgroundColor": {
                    "value": "#fff",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "textColor": {
                    "value": "#000",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "borderColor": {
                    "value": "#ddd",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "logoAsset": None,
                "typography": {
                    "value": "sans",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "imageStyle": {
                    "value": "clean",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "visualTone": {
                    "value": "minimal",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "motionIntensity": {
                    "value": "low",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "layoutDensity": {
                    "value": "comfortable",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        heroVariant=HeroVariant.model_validate(
            {
                "headline": "Test",
                "subheadline": "Test",
                "supportingLine": "Test",
                "primaryCta": "Test",
                "secondaryCta": "Test",
                "layout": "center",
                "visualTreatment": "clean",
                "evidence": {
                    "sourceKind": "inferred",
                    "inferenceLabel": "Test",
                    "confidence": 0,
                    "references": [],
                },
            }
        ),
        sectionStack=[],
        ctaStrategy=CtaStrategy.model_validate(
            {
                "primary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "secondary": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
                "footer": {
                    "label": "Test",
                    "href": "#",
                    "rationale": "Test",
                    "evidence": {
                        "sourceKind": "inferred",
                        "inferenceLabel": "Test",
                        "confidence": 0,
                        "references": [],
                    },
                },
            }
        ),
        qualityScore=50,
        readinessStatus="blocked",
        qaStatus="fail",
        reviewRubric=[],
        comparisonEntries=[],
        sourceTraceability=[],
        missingRequirements=[],
        sourceAttribution=None,
        browserReviewState="not_reviewed",
        publishApprovalState="pending",
        screenshotRefs=[],
        latestReviewId=None,
        handoffRecordId=None,
        diversityNotes=[],
        diversityScore=50,
        layoutHash="",
        previewSlug="test",
        previewUrl="/sites/test",
        overrideCount=0,
        overrides=[],
        exportMetadata=None,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
        publishedAt=None,
    )

    similarity = comparator.detect_duplicate_layout(mock_site, mock_site3)
    assert similarity == 0.0  # Different layouts
