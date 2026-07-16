"""Tests for extraction enrichment — Phase 1 content quality validation and LLM enrichment."""

import pytest

from app.core.extraction_enrichment import (
    enrich_extraction,
    validate_extraction_content,
)


def test_validate_extraction_content_valid():
    """Valid extraction with enough content passes validation."""
    crawl_data = {
        "summary": {
            "serviceClues": ["Service 1", "Service 2", "Service 3"],
            "audienceClues": ["For developers", "For teams"],
            "positioningSummary": "Company X provides payment processing",
        },
        "sectionInventory": [
            {"text": "A" * 300},
            {"text": "B" * 300},
        ],
        "pageInventory": [
            {"cleanedText": "C" * 300},
        ],
    }
    is_valid, issues = validate_extraction_content(crawl_data)
    assert is_valid
    assert len(issues) == 0


def test_validate_extraction_content_sparse():
    """Sparse extraction fails validation with specific issues."""
    crawl_data = {
        "summary": {
            "serviceClues": [],
            "audienceClues": ["For developers"],
            "positioningSummary": "Short",
        },
        "sectionInventory": [
            {"text": "Too little"},
        ],
        "pageInventory": [],
    }
    is_valid, issues = validate_extraction_content(crawl_data)
    assert not is_valid
    assert len(issues) >= 3
    assert any("chars extracted" in issue for issue in issues)
    assert any("services found" in issue for issue in issues)
    assert any("audience clues" in issue for issue in issues)


def test_validate_extraction_content_missing_positioning():
    """Missing positioning summary is flagged."""
    crawl_data = {
        "summary": {
            "serviceClues": ["S1", "S2", "S3"],
            "audienceClues": ["For teams", "For developers"],
            "positioningSummary": None,
        },
        "sectionInventory": [{"text": "X" * 600}],
        "pageInventory": [],
    }
    is_valid, issues = validate_extraction_content(crawl_data)
    assert not is_valid
    assert any("Positioning summary" in issue for issue in issues)


@pytest.mark.asyncio
async def test_enrich_extraction_too_sparse():
    """Enrichment skips if content is below minimum threshold."""
    crawl_data = {
        "summary": {
            "serviceClues": [],
            "audienceClues": [],
            "positioningSummary": None,
        },
        "sectionInventory": [],
        "pageInventory": [{"cleanedText": "Too short"}],
        "gapItems": [],
    }

    await enrich_extraction(crawl_data)

    # Should add gap item indicating it was too sparse
    assert "content_too_sparse_for_enrichment" in crawl_data["gapItems"]
    # Summary should remain empty
    assert len(crawl_data["summary"]["serviceClues"]) == 0


@pytest.mark.asyncio
async def test_enrich_extraction_with_mock_llm(monkeypatch):
    """Enrichment uses LLM to infer missing data."""

    class MockLLM:
        async def generate_text(self, prompt, temperature=0.7, max_tokens=2048):
            if "services" in prompt.lower():
                return '["Payment processing", "Billing management", "Fraud detection"]'
            if "audience" in prompt.lower():
                return '["For startups", "For developers"]'
            if "positioning" in prompt.lower():
                return "Company provides payment infrastructure for online businesses"
            return "[]"

        def extract_json_from_response(self, response):
            import json

            return json.loads(response)

    mock_llm = MockLLM()

    def mock_get_llm_client():
        return mock_llm

    monkeypatch.setattr(
        "app.core.extraction_enrichment.get_llm_client", mock_get_llm_client
    )

    crawl_data = {
        "summary": {
            "companyName": "TestCo",
            "serviceClues": [],
            "audienceClues": [],
            "positioningSummary": None,
        },
        "sectionInventory": [
            {
                "heading": "Our Services",
                "text": "We help businesses process payments online. " * 50,
            },
            {
                "heading": "For Developers",
                "text": "Built for developers who need reliable APIs. " * 50,
            },
        ],
        "pageInventory": [
            {"cleanedText": "Payment processing made simple. " * 30},
        ],
        "gapItems": [],
    }

    await enrich_extraction(crawl_data)

    # Should have enriched services
    assert len(crawl_data["summary"]["serviceClues"]) >= 3
    assert "Payment processing" in crawl_data["summary"]["serviceClues"]

    # Should have enriched audience
    assert len(crawl_data["summary"]["audienceClues"]) >= 2

    # Should have enriched positioning
    assert crawl_data["summary"]["positioningSummary"] is not None
    assert len(crawl_data["summary"]["positioningSummary"]) > 30

    # Should mark as enriched
    assert "llm_enriched" in crawl_data["gapItems"]


@pytest.mark.asyncio
async def test_enrich_extraction_merges_with_existing(monkeypatch):
    """Enrichment merges with existing data, doesn't replace."""

    class MockLLM:
        async def generate_text(self, prompt, temperature=0.7, max_tokens=2048):
            if "services" in prompt.lower():
                return '["New Service 1", "New Service 2"]'
            return "[]"

        def extract_json_from_response(self, response):
            import json

            return json.loads(response)

    monkeypatch.setattr(
        "app.core.extraction_enrichment.get_llm_client", lambda: MockLLM()
    )

    crawl_data = {
        "summary": {
            "companyName": "TestCo",
            "serviceClues": ["Existing Service"],
            "audienceClues": ["For developers", "For teams"],
            "positioningSummary": "Existing positioning",
        },
        "sectionInventory": [{"text": "Content " * 100}],
        "pageInventory": [],
        "gapItems": [],
    }

    await enrich_extraction(crawl_data)

    # Should merge new services with existing
    assert "Existing Service" in crawl_data["summary"]["serviceClues"]
    assert "New Service 1" in crawl_data["summary"]["serviceClues"]

    # Should not touch audience (already has 2)
    assert crawl_data["summary"]["audienceClues"] == ["For developers", "For teams"]

    # Should not touch positioning (already exists)
    assert crawl_data["summary"]["positioningSummary"] == "Existing positioning"
