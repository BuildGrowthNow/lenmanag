import pytest
from unittest.mock import AsyncMock, patch
from app.core.screenshot_comparator import ScreenshotComparator
from app.schemas.site import (
    GeneratedSite,
    SiteSection,
    HeroVariant,
    CtaStrategy,
    CtaAction,
    BrandTokens,
    SiteToken,
    BriefEvidence,
)


@pytest.fixture
def screenshot_comparator():
    """Create a screenshot comparator instance for testing."""
    return ScreenshotComparator()


@pytest.fixture
def sample_generated_site():
    """Create a sample generated site for testing."""
    from datetime import datetime

    now = datetime.utcnow()

    return GeneratedSite(
        id="test-site-123",
        leadId="test-site-123",
        generationJobId="job-123",
        briefId="brief-123",
        briefVersion=1,
        version=1,
        themeId="theme-1",
        themeKey="editorial-frame",
        themeName="Editorial Frame",
        themeRationale="Selected for premium feel",
        paletteMode="light",
        paletteRationale="Neutral palette",
        overrideCount=0,
        createdAt=now,
        updatedAt=now,
        brandTokens=BrandTokens(
            paletteMode="light",
            primaryColor=SiteToken(
                value="#334155",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            secondaryColor=SiteToken(
                value="#64748b",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            accentColor=SiteToken(
                value="#0ea5e9",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            backgroundColor=SiteToken(
                value="#ffffff",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            textColor=SiteToken(
                value="#000000",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            borderColor=SiteToken(
                value="#e2e8f0",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            logoAsset=None,
            typography=SiteToken(
                value="sans-serif",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            imageStyle=SiteToken(
                value="photography",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            visualTone=SiteToken(
                value="professional",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            motionIntensity=SiteToken(
                value="subtle",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
            layoutDensity=SiteToken(
                value="spacious",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Default",
                    confidence=70,
                    references=[],
                ),
            ),
        ),
        heroVariant=HeroVariant(
            headline="Welcome to our site",
            subheadline="A great experience",
            supportingLine="Learn more about us",
            primaryCta="Get started",
            secondaryCta="Learn more",
            layout="split-editorial",
            visualTreatment="monochrome with accent",
            evidence=BriefEvidence(
                sourceKind="inferred",
                inferenceLabel="Generated",
                confidence=70,
                references=[],
            ),
        ),
        sectionStack=[
            SiteSection(
                kind="services",
                title="Services",
                headline="Our Services",
                body="We offer amazing services",
                items=["Service 1", "Service 2"],
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Generated",
                    confidence=70,
                    references=[],
                ),
            )
        ],
        ctaStrategy=CtaStrategy(
            primary=CtaAction(
                label="Get started",
                href="#contact",
                rationale="Primary CTA",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Generated",
                    confidence=70,
                    references=[],
                ),
            ),
            secondary=CtaAction(
                label="Learn more",
                href="#sections",
                rationale="Secondary CTA",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Generated",
                    confidence=70,
                    references=[],
                ),
            ),
            footer=CtaAction(
                label="Contact",
                href="#contact",
                rationale="Footer CTA",
                evidence=BriefEvidence(
                    sourceKind="inferred",
                    inferenceLabel="Generated",
                    confidence=70,
                    references=[],
                ),
            ),
        ),
        qualityScore=75,
        readinessStatus="ready_for_review",
        qaStatus="warn",
        reviewRubric=[],
        comparisonEntries=[],
        sourceTraceability=[],
        missingRequirements=[],
        previewSlug="test-site-123",
        previewUrl="/sites/test-site-123",
    )


class TestScreenshotComparator:
    """Test ScreenshotComparator class."""

    def test_compute_layout_hash(self, screenshot_comparator, sample_generated_site):
        """Test layout hash computation."""
        hash1 = screenshot_comparator.compute_layout_hash(sample_generated_site)
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 hex string length

    def test_compute_layout_hash_deterministic(
        self, screenshot_comparator, sample_generated_site
    ):
        """Test that layout hash is deterministic."""
        hash1 = screenshot_comparator.compute_layout_hash(sample_generated_site)
        hash2 = screenshot_comparator.compute_layout_hash(sample_generated_site)
        assert hash1 == hash2

    def test_detect_duplicate_layout_identical(
        self, screenshot_comparator, sample_generated_site
    ):
        """Test detecting identical layouts."""
        similarity = screenshot_comparator.detect_duplicate_layout(
            sample_generated_site, sample_generated_site
        )
        assert similarity == 1.0

    def test_detect_duplicate_layout_different(
        self, screenshot_comparator, sample_generated_site
    ):
        """Test detecting different layouts."""
        site2 = sample_generated_site.model_copy()
        site2.themeKey = "color-study"

        similarity = screenshot_comparator.detect_duplicate_layout(
            sample_generated_site, site2
        )
        assert similarity == 0.0

    @pytest.mark.asyncio
    async def test_compare_layout_screenshot_success(self, screenshot_comparator):
        """Test successful screenshot comparison."""
        mock_analyzer = AsyncMock()
        mock_analyzer.capture_screenshots = AsyncMock(
            return_value={
                "desktopScreenshot": b"test",
                "mobileScreenshot": b"test",
                "desktopUrl": "screenshots/site-123/desktop.png",
                "mobileUrl": "screenshots/site-123/mobile.png",
                "layoutHash": "abc123",
                "capturedAt": "2024-05-31T12:00:00Z",
            }
        )
        mock_analyzer.perform_qa_analysis = AsyncMock(
            return_value={
                "qualityScore": 82,
                "sectionScores": [
                    {
                        "sectionTitle": "Hero",
                        "score": 90,
                        "critique": "Good",
                        "recommendation": None,
                    }
                ],
                "rawCritique": "Good design",
                "readinessAssessment": "production_ready",
                "passThreshold": True,
            }
        )

        with patch(
            "app.core.screenshot_comparator.get_screenshot_analyzer",
            return_value=mock_analyzer,
        ):
            result = await screenshot_comparator.compare_layout_screenshot(
                site_id="site-123",
                preview_url="/sites/site-123",
            )

            # Verify result
            assert result["success"] is True
            assert result["qualityScore"] == 82
            assert result["passThreshold"] is True
            assert "desktopScreenshotUrl" in result
            assert "mobileScreenshotUrl" in result
            assert "layoutHash" in result

    @pytest.mark.asyncio
    async def test_compare_layout_screenshot_failure(self, screenshot_comparator):
        """Test screenshot comparison failure handling."""
        mock_analyzer = AsyncMock()
        mock_analyzer.capture_screenshots = AsyncMock(
            side_effect=Exception("Capture failed")
        )

        with patch(
            "app.core.screenshot_comparator.get_screenshot_analyzer",
            return_value=mock_analyzer,
        ):
            result = await screenshot_comparator.compare_layout_screenshot(
                site_id="site-123",
                preview_url="/sites/site-123",
            )

            # Should return error result
            assert result["success"] is False
            assert "error" in result
            assert result["qualityScore"] == 0
            assert result["passThreshold"] is False


class TestIntegrationWithAnalyzer:
    """Integration tests with ScreenshotAnalyzer."""

    @pytest.mark.asyncio
    async def test_end_to_end_screenshot_and_qa(self):
        """Test end-to-end screenshot capture and QA."""
        comparator = ScreenshotComparator()

        mock_analyzer = AsyncMock()
        screenshot_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        mock_analyzer.capture_screenshots = AsyncMock(
            return_value={
                "desktopScreenshot": screenshot_bytes,
                "mobileScreenshot": screenshot_bytes,
                "desktopUrl": "screenshots/site-123/desktop.png",
                "mobileUrl": "screenshots/site-123/mobile.png",
                "layoutHash": "layout-hash-abc123",
                "capturedAt": "2024-05-31T12:00:00Z",
            }
        )

        mock_analyzer.perform_qa_analysis = AsyncMock(
            return_value={
                "qualityScore": 88,
                "sectionScores": [
                    {
                        "sectionTitle": "Hero",
                        "score": 95,
                        "critique": "Excellent hero",
                        "recommendation": None,
                    },
                    {
                        "sectionTitle": "Services",
                        "score": 85,
                        "critique": "Good services section",
                        "recommendation": None,
                    },
                    {
                        "sectionTitle": "CTA",
                        "score": 82,
                        "critique": "Clear CTA",
                        "recommendation": "Add more spacing",
                    },
                ],
                "rawCritique": "Overall excellent design with strong visual hierarchy",
                "readinessAssessment": "production_ready",
                "passThreshold": True,
            }
        )

        with patch(
            "app.core.screenshot_comparator.get_screenshot_analyzer",
            return_value=mock_analyzer,
        ):
            result = await comparator.compare_layout_screenshot(
                site_id="site-123",
                preview_url="/sites/site-123",
            )

            # Comprehensive verification
            assert result["success"] is True
            assert result["qualityScore"] == 88
            assert result["passThreshold"] is True
            assert result["readinessAssessment"] == "production_ready"
            assert len(result["sectionScores"]) == 3
            assert result["desktopScreenshotUrl"] == "screenshots/site-123/desktop.png"
            assert result["mobileScreenshotUrl"] == "screenshots/site-123/mobile.png"
            assert result["layoutHash"] == "layout-hash-abc123"
