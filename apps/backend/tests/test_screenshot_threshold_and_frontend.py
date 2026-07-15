from pathlib import Path

import pytest
from unittest.mock import AsyncMock, patch

from app.core.screenshot_comparator import ScreenshotComparator
from app.core.config import Settings


@pytest.mark.asyncio
async def test_screenshot_comparator_uses_configured_quality_threshold(monkeypatch):
    """ScreenshotComparator passes visual_redesign_quality_threshold from settings to analyzer."""

    class DummySettings(Settings):
        visual_redesign_quality_threshold: int = 92

    monkeypatch.setattr("app.core.screenshot_comparator.get_settings", lambda: DummySettings())

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
            "qualityScore": 80,
            "sectionScores": [],
            "rawCritique": "",
            "readinessAssessment": "needs_refinement",
            "passThreshold": False,
        }
    )

    comparator = ScreenshotComparator()

    with patch(
        "app.core.screenshot_comparator.get_screenshot_analyzer", return_value=mock_analyzer
    ):
        await comparator.compare_layout_screenshot(
            site_id="site-123",
            preview_url="/sites/site-123",
        )

    mock_analyzer.perform_qa_analysis.assert_awaited_once()
    _args, kwargs = mock_analyzer.perform_qa_analysis.call_args
    assert kwargs.get("quality_threshold") == 92


def test_settings_visual_redesign_quality_threshold_default_is_90():
    settings = Settings()
    assert settings.visual_redesign_quality_threshold == 90


def test_premium_registry_contains_phase14_components():
    """Ensure backend componentIds for premium sections exist in frontend registry."""

    # Locate repo root relative to this test file
    here = Path(__file__).resolve()
    repo_root = here.parents[3]
    registry_path = repo_root / "apps" / "web" / "src" / "components" / "premium-sections.tsx"

    contents = registry_path.read_text(encoding="utf-8")

    for component_id in [
        "hero-split-editorial",
        "services-bento",
        "proof-carousel",
        "timeline-vertical",
        "gallery-masonry",
        "editorial-feature",
        "cta-banner",
        "cta-sticky",
    ]:
        assert component_id in contents, f"Missing premium componentId in frontend registry: {component_id}"
