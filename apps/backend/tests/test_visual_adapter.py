from types import SimpleNamespace

from app.core.variant_strategy import get_variant_strategies
from app.core.visual_adapter import build_art_direction_plan, build_visual_adapter, select_capabilities


def _extraction(text: str):
    return SimpleNamespace(
        summary=SimpleNamespace(companyName="Example", positioningSummary=text, audienceClues=[], serviceClues=[], toneClues=[]),
        analysis=SimpleNamespace(positioning=text, audience="buyers", services=[], tone="clear", valueProposition="",),
        extractedImages=[], sectionInventory=[],
    )


def test_adapter_uses_evidence_and_changes_by_industry():
    restaurant = build_visual_adapter(_extraction("restaurant menu dining ingredients reservation"))
    clinic = build_visual_adapter(_extraction("clinic patient treatment appointment accessibility"))
    assert restaurant["industry"] == "restaurant"
    assert clinic["industry"] == "clinic"
    assert restaurant["interaction"] != clinic["interaction"]
    assert "menu rhythm" in restaurant["interaction"]


def test_plans_are_distinct_and_capabilities_have_fallbacks():
    adapter = build_visual_adapter(_extraction("architecture project materials spatial studio"))
    strategies = get_variant_strategies(adapter=adapter)
    concepts = [strategies[key]["artDirectionPlan"]["creativeConcept"] for key in ("html_v1", "html_v2", "html_v3")]
    assert len(set(concepts)) == 3
    capabilities = select_capabilities(adapter, "html_v2")
    assert capabilities["fallbacks"][capabilities["allowed"][0]] == "semantic HTML and CSS"
    assert build_art_direction_plan(adapter, strategies["html_v1"])["fallbackPlan"]

