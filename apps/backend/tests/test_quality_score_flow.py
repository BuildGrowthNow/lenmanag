from types import SimpleNamespace

import pytest

pytest.importorskip("mongomock")

from app.core.sites import _quality_score, site_repository


def _inputs(*, approved=True, missing=None):
    brief = SimpleNamespace(
        approvalState="approved" if approved else "draft",
        recommendedSections=["Hero", "Services", "CTA"],
        proofPoints=["Proof"],
        confidenceScore=90,
        visualRedesign=["direction"],
    )
    extraction = SimpleNamespace(
        sourceCitations=[1, 2, 3], brandAssetCues=[1, 2], pagesCrawled=4,
        extractedTestimonials=[1], extractedImages=[1], confidenceScore=90,
    )
    tokens = {"primaryColor": {"evidence": {"sourceKind": "source_backed"}}, "typography": {"evidence": {"sourceKind": "source_backed"}}}
    return dict(brief=brief, extraction=extraction, brand_tokens=tokens, site_sections=[], missing_requirements=missing or [])


def test_complete_fallback_score_is_not_stuck_in_low_thirties():
    score = _quality_score(**_inputs())
    assert 70 <= score <= 100


def test_incomplete_fallback_score_is_low_and_bounded():
    score = _quality_score(**_inputs(approved=False, missing=["copy", "images", "cta", "brand", "sections"]))
    assert 0 <= score < 70


def test_visual_score_is_primary_and_bounded():
    assert _quality_score(**_inputs(), screenshot_qa_score=84) == 88
    assert 0 <= _quality_score(**_inputs(), screenshot_qa_score=999) <= 100


@pytest.mark.asyncio
async def test_visual_recalculation_replaces_fallback_in_memory():
    site_repository._sites["quality-test"] = {"id": "quality-test", "qualityScore": 34, "qualityScoreSource": "fallback"}
    await site_repository.persist_visual_quality("quality-test", 82, {"available": True})
    assert site_repository._sites["quality-test"]["qualityScore"] == 82
    assert site_repository._sites["quality-test"]["qualityScoreSource"] == "visual"
    site_repository._sites.pop("quality-test", None)
