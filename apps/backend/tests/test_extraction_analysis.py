import pytest
from datetime import datetime, timezone
from app.core.extraction_analysis import analyze_extraction, _build_analysis_context, _validate_analysis, _empty_analysis
from app.schemas.extraction import ExtractionSnapshot, ExtractionSummary


@pytest.mark.asyncio
async def test_analyze_extraction_returns_valid_structure():
    """Test that analyze_extraction returns data with expected fields."""
    # Create a minimal extraction snapshot
    extraction = ExtractionSnapshot(
        id="test-extraction-1",
        leadId="test-lead-1",
        version=1,
        crawlStatus="completed",
        sitemapStatus="found",
        pagesDiscovered=5,
        pagesCrawled=5,
        canonicalWebsiteUrl="https://example.com",
        summary=ExtractionSummary(
            companyName="Test Company",
            canonicalWebsiteUrl="https://example.com",
            positioningSummary="A test company",
            serviceClues=["Service 1", "Service 2"],
            ctaClues=["Contact Us", "Get Started"],
            toneClues=["professional"],
            audienceClues=["businesses"],
        ),
        confidenceScore=85,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    # Mock the LLM client to avoid real API calls
    from unittest.mock import AsyncMock, patch

    mock_response = """{
        "services": ["Service 1", "Service 2"],
        "tone": "Professional and friendly",
        "primaryCTAs": ["Contact Us", "Get Started"],
        "audience": "Small businesses",
        "valueProposition": "We help businesses grow",
        "positioning": "A company that helps businesses",
        "confidence": 85
    }"""

    with patch("app.core.extraction_analysis.get_llm_client") as mock_llm:
        mock_client = AsyncMock()
        mock_client.generate_text = AsyncMock(return_value=mock_response)
        mock_client.extract_json_from_response = lambda _: {
            "services": ["Service 1", "Service 2"],
            "tone": "Professional and friendly",
            "primaryCTAs": ["Contact Us", "Get Started"],
            "audience": "Small businesses",
            "valueProposition": "We help businesses grow",
            "positioning": "A company that helps businesses",
            "confidence": 85
        }
        mock_llm.return_value = mock_client

        result = await analyze_extraction(extraction)

        assert "services" in result
        assert "tone" in result
        assert "primaryCTAs" in result
        assert "audience" in result
        assert "valueProposition" in result
        assert "positioning" in result
        assert "confidence" in result


def test_validate_analysis_cleans_data():
    """Test that validate_analysis cleans and validates data."""
    analysis = {
        "services": ["Service 1", "Service 2", "S"],  # S is too short
        "tone": "Professional tone description",
        "primaryCTAs": ["Contact", "Get Quote"],
        "audience": "Target audience",
        "valueProposition": "We are great",
        "positioning": "We do X, Y, Z",
        "confidence": 85,
    }

    result = _validate_analysis(analysis)

    assert len(result["services"]) == 2  # S should be filtered out
    assert result["tone"] == "Professional tone description"
    assert len(result["primaryCTAs"]) == 2
    assert result["confidence"] == 85


def test_validate_analysis_handles_missing_fields():
    """Test that validate_analysis provides defaults for missing fields."""
    analysis = {
        "services": [],
        "confidence": 50,
    }

    result = _validate_analysis(analysis)

    assert result["services"] == []
    assert result["tone"] == "Professional"
    assert result["primaryCTAs"] == []
    assert result["audience"] == "General audience"
    assert result["confidence"] == 50


def test_empty_analysis():
    """Test that _empty_analysis returns valid empty structure."""
    result = _empty_analysis()

    assert result["services"] == []
    assert result["tone"] == "Professional"
    assert result["primaryCTAs"] == []
    assert result["audience"] == "General audience"
    assert result["valueProposition"] == ""
    assert result["positioning"] == ""
    assert result["confidence"] == 0


def test_build_analysis_context_handles_empty_inventory():
    """Test that _build_analysis_context handles empty page/section inventory."""
    extraction = ExtractionSnapshot(
        id="test-extraction-1",
        leadId="test-lead-1",
        version=1,
        crawlStatus="completed",
        sitemapStatus="missing",
        pagesDiscovered=0,
        pagesCrawled=0,
        canonicalWebsiteUrl="https://example.com",
        summary=ExtractionSummary(
            companyName="Test Company",
            canonicalWebsiteUrl="https://example.com",
            positioningSummary="A test company",
        ),
        confidenceScore=50,
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )

    context = _build_analysis_context(extraction)

    assert context["company_name"] == "Test Company"
    assert context["website_url"] == "https://example.com"
    assert context["homepage_text"] == ""
    assert context["section_headings"] == []
    assert context["section_texts"] == []
