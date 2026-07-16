import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.visual_redesign import VisualRedesignAnalyzer
from app.schemas.brief import VisualCritique
from app.schemas.extraction import ExtractedSection


@pytest.fixture
def mock_visual_gemini_client(monkeypatch):
    """Provide a mocked Gemini client for VisualRedesignAnalyzer tests."""

    mock_client = MagicMock()
    mock_client.generate_text = AsyncMock(return_value="{}")
    mock_client.extract_json_from_response.return_value = {
        "sectionType": "services",
        "originalStrengths": ["Clear offering"],
        "originalWeaknesses": ["Layout is basic"],
        "redesignGoal": "Make services section feel more premium",
        "contentToReuse": ["We offer web design and development"],
        "contentToRewrite": ["Web design and development"],
        "recommendedComponent": "services-bento",
        "visualDirection": "Premium bento grid with strong hierarchy",
        "confidence": 90,
    }

    monkeypatch.setattr(
        "app.core.visual_redesign.get_llm_client",
        lambda: mock_client,
    )
    return mock_client


@pytest.mark.asyncio
async def test_analyze_section_returns_valid_critique(mock_visual_gemini_client):
    """Test that section analysis returns valid critique."""
    analyzer = VisualRedesignAnalyzer()

    section = ExtractedSection(
        id="section-1",
        index=0,
        type="services",
        tagName="section",
        heading="Our Services",
        text="We offer web design and development",
        ctas=["Web Design", "Development"],
    )

    client_brand = {
        "paletteMode": "light",
        "primaryColor": {"value": "#000"},
        "accentColor": {"value": "#f97316"},
        "typography": {"value": "sans-serif"},
    }

    critique = await analyzer.analyze_section(section, client_brand, 0)

    assert isinstance(critique, VisualCritique)
    assert critique.sectionType == "services"
    assert critique.recommendedComponent in {
        c["id"] for c in analyzer.AVAILABLE_COMPONENTS
    }
    assert critique.confidence > 0


@pytest.mark.asyncio
async def test_analyze_section_handles_errors(mock_visual_gemini_client):
    """Test that section analysis handles errors gracefully."""

    # Force the mocked client to raise so we hit the error path
    mock_visual_gemini_client.generate_text.side_effect = Exception("LLM failure")
    analyzer = VisualRedesignAnalyzer()

    section = ExtractedSection(
        id="section-2",
        index=1,
        type="unknown",
        tagName="div",
        heading="",
        text="",
        ctas=[],
    )

    client_brand = {}

    # Should not raise, should return safe default
    critique = await analyzer.analyze_section(section, client_brand, 0)
    assert critique is not None
    assert critique.confidence >= 0
