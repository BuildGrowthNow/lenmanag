import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.screenshot_analyzer import ScreenshotAnalyzer, get_screenshot_analyzer
from app.core.gemini_client import GeminiClient


@pytest.fixture
def screenshot_analyzer():
    """Create a screenshot analyzer instance for testing."""
    return ScreenshotAnalyzer()


@pytest.fixture
def mock_screenshot_bytes():
    """Mock PNG screenshot bytes."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client."""
    client = AsyncMock(spec=GeminiClient)
    client.analyze_image = AsyncMock()
    client.generate_text = AsyncMock()
    client.extract_json_from_response = MagicMock()
    return client


class TestScreenshotAnalyzer:
    """Test ScreenshotAnalyzer class."""

    def test_available_components(self, screenshot_analyzer):
        """Test that AVAILABLE_COMPONENTS is properly defined."""
        assert len(screenshot_analyzer.AVAILABLE_COMPONENTS) > 0
        assert all("id" in c for c in screenshot_analyzer.AVAILABLE_COMPONENTS)
        assert all("name" in c for c in screenshot_analyzer.AVAILABLE_COMPONENTS)
        assert all("description" in c for c in screenshot_analyzer.AVAILABLE_COMPONENTS)

    def test_available_components_have_valid_ids(self, screenshot_analyzer):
        """Test that component IDs follow naming conventions."""
        valid_prefixes = [
            "hero-",
            "services-",
            "proof-",
            "gallery-",
            "timeline-",
            "cta-",
            "editorial-",
        ]
        for component in screenshot_analyzer.AVAILABLE_COMPONENTS:
            component_id = component["id"]
            assert any(
                component_id.startswith(prefix) for prefix in valid_prefixes
            ), f"Component {component_id} doesn't have valid prefix"

    @pytest.mark.asyncio
    async def test_capture_screenshots_success(
        self, screenshot_analyzer, mock_screenshot_bytes
    ):
        """Test successful screenshot capture."""
        with patch("app.core.screenshot_analyzer.async_playwright") as mock_pw:
            # Setup mock Playwright
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_page.screenshot = AsyncMock(return_value=mock_screenshot_bytes)
            mock_page.goto = AsyncMock()
            mock_page.close = AsyncMock()

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value.chromium.launch = AsyncMock(
                return_value=mock_browser
            )
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()
            mock_pw.return_value.__aenter__.return_value = mock_context_manager.__aenter__.return_value

            # Call capture_screenshots
            result = await screenshot_analyzer.capture_screenshots(
                site_id="test-site-123",
                preview_url="/sites/test-site-123",
            )

            # Verify result structure
            assert result["desktopScreenshot"] == mock_screenshot_bytes
            assert result["mobileScreenshot"] == mock_screenshot_bytes
            assert result["desktopUrl"] == "screenshots/test-site-123/desktop.png"
            assert result["mobileUrl"] == "screenshots/test-site-123/mobile.png"
            assert "layoutHash" in result
            assert result["layoutHash"]  # Hash should be non-empty
            assert "capturedAt" in result

    @pytest.mark.asyncio
    async def test_capture_screenshots_failure_handling(self, screenshot_analyzer):
        """Test screenshot capture failure handling."""
        with patch("app.core.screenshot_analyzer.async_playwright") as mock_pw:
            mock_pw.side_effect = Exception("Browser launch failed")

            # Should raise exception
            with pytest.raises(Exception, match="Browser launch failed"):
                await screenshot_analyzer.capture_screenshots(
                    site_id="test-site-123",
                    preview_url="/sites/test-site-123",
                )

    @pytest.mark.asyncio
    async def test_perform_qa_analysis_success(
        self, screenshot_analyzer, mock_screenshot_bytes, mock_gemini_client
    ):
        """Test successful QA analysis."""
        qa_response = """{
            "qualityScore": 82,
            "sectionScores": [
                {"sectionTitle": "Hero", "score": 90, "critique": "Strong hero section", "recommendation": null},
                {"sectionTitle": "Services", "score": 78, "critique": "Could improve spacing", "recommendation": "Add more padding"}
            ],
            "overallCritique": "Good design with strong typography",
            "readinessAssessment": "production_ready"
        }"""

        with patch(
            "app.core.screenshot_analyzer.get_llm_client", return_value=mock_gemini_client
        ):
            mock_gemini_client.analyze_image.return_value = qa_response
            mock_gemini_client.extract_json_from_response.return_value = {
                "qualityScore": 82,
                "sectionScores": [
                    {
                        "sectionTitle": "Hero",
                        "score": 90,
                        "critique": "Strong hero section",
                        "recommendation": None,
                    }
                ],
                "overallCritique": "Good design with strong typography",
                "readinessAssessment": "production_ready",
            }

            result = await screenshot_analyzer.perform_qa_analysis(
                site_id="test-site-123",
                desktop_screenshot=mock_screenshot_bytes,
                extraction_summary="Test site summary",
                section_stack=["Hero", "Services", "CTA"],
                quality_threshold=75,
            )

            # Verify result structure
            assert result["qualityScore"] == 82
            assert result["passThreshold"] is True
            assert len(result["sectionScores"]) > 0
            assert result["readinessAssessment"] == "production_ready"
            assert "rawCritique" in result

    @pytest.mark.asyncio
    async def test_perform_qa_analysis_below_threshold(
        self, screenshot_analyzer, mock_screenshot_bytes, mock_gemini_client
    ):
        """Test QA analysis when quality is below threshold."""
        qa_response = """{
            "qualityScore": 65,
            "sectionScores": [],
            "overallCritique": "Design needs refinement",
            "readinessAssessment": "needs_refinement"
        }"""

        with patch(
            "app.core.screenshot_analyzer.get_llm_client", return_value=mock_gemini_client
        ):
            mock_gemini_client.analyze_image.return_value = qa_response
            mock_gemini_client.extract_json_from_response.return_value = {
                "qualityScore": 65,
                "sectionScores": [],
                "overallCritique": "Design needs refinement",
                "readinessAssessment": "needs_refinement",
            }

            result = await screenshot_analyzer.perform_qa_analysis(
                site_id="test-site-123",
                desktop_screenshot=mock_screenshot_bytes,
                extraction_summary="Test site summary",
                section_stack=["Hero", "Services"],
                quality_threshold=75,
            )

            # Verify threshold check
            assert result["qualityScore"] == 65
            assert result["passThreshold"] is False
            assert result["readinessAssessment"] == "needs_refinement"

    @pytest.mark.asyncio
    async def test_perform_qa_analysis_invalid_json_response(
        self, screenshot_analyzer, mock_screenshot_bytes, mock_gemini_client
    ):
        """Test QA analysis handles invalid JSON response."""
        with patch(
            "app.core.screenshot_analyzer.get_llm_client", return_value=mock_gemini_client
        ):
            mock_gemini_client.analyze_image.return_value = "Invalid JSON response"
            mock_gemini_client.extract_json_from_response.side_effect = ValueError(
                "Invalid JSON"
            )

            result = await screenshot_analyzer.perform_qa_analysis(
                site_id="test-site-123",
                desktop_screenshot=mock_screenshot_bytes,
                extraction_summary="Test site summary",
                section_stack=["Hero", "Services"],
            )

            # Should fallback to conservative default values
            assert result["qualityScore"] == 30
            assert result["sectionScores"] == []
            assert result["passThreshold"] is False

    @pytest.mark.asyncio
    async def test_generate_improvement_brief_success(
        self, screenshot_analyzer, mock_gemini_client
    ):
        """Test successful improvement brief generation."""
        improvement_response = """{
            "overallApproach": "Increase visual hierarchy and spacing",
            "sectionImprovements": [
                {
                    "sectionTitle": "Hero",
                    "currentIssues": ["Low contrast"],
                    "recommendedChanges": ["Increase contrast ratio"],
                    "priority": "high"
                }
            ],
            "estimatedNewScore": 85,
            "implementationNotes": "Focus on hierarchy"
        }"""

        with patch(
            "app.core.screenshot_analyzer.get_llm_client", return_value=mock_gemini_client
        ):
            mock_gemini_client.generate_text.return_value = improvement_response
            mock_gemini_client.extract_json_from_response.return_value = {
                "overallApproach": "Increase visual hierarchy and spacing",
                "sectionImprovements": [
                    {
                        "sectionTitle": "Hero",
                        "currentIssues": ["Low contrast"],
                        "recommendedChanges": ["Increase contrast ratio"],
                        "priority": "high",
                    }
                ],
                "estimatedNewScore": 85,
                "implementationNotes": "Focus on hierarchy",
            }

            result = await screenshot_analyzer.generate_improvement_brief(
                site_id="test-site-123",
                extraction_summary="Test extraction",
                section_stack=["Hero", "Services"],
                qa_critique="Quality below threshold",
                brand_summary="Brand info",
            )

            # Verify result structure
            assert "overallApproach" in result
            assert "sectionImprovements" in result
            assert result["estimatedNewScore"] == 85
            assert len(result["sectionImprovements"]) > 0

    def test_compare_screenshots_identical(
        self, screenshot_analyzer, mock_screenshot_bytes
    ):
        """Test comparing identical screenshots."""
        similarity = screenshot_analyzer.compare_screenshots(
            mock_screenshot_bytes, mock_screenshot_bytes
        )
        assert similarity == 1.0

    def test_compare_screenshots_different(
        self, screenshot_analyzer, mock_screenshot_bytes
    ):
        """Test comparing different screenshots."""
        screenshot2 = b"\x89PNG\r\n\x1a\n" + b"\x01" * 100
        similarity = screenshot_analyzer.compare_screenshots(
            mock_screenshot_bytes, screenshot2
        )
        assert similarity == 0.0

    def test_singleton_instance(self):
        """Test that get_screenshot_analyzer returns singleton."""
        analyzer1 = get_screenshot_analyzer()
        analyzer2 = get_screenshot_analyzer()
        assert analyzer1 is analyzer2
