from app.core.site_quality_metrics import build_quality_gate_report
from app.core.rollout import publish_allowed, rollout_decision


def test_quality_gate_report_keeps_hard_failures_visible() -> None:
    report = build_quality_gate_report({"visualQuality": 98, "footer": True})
    assert "evidenceSafety" in report["hardFailures"]
    assert report["publishable"] is False


def test_quality_gate_report_distinguishes_unmeasured_from_failed() -> None:
    report = build_quality_gate_report(
        {
            "evidenceSafety": None,
            "brandFidelity": None,
            "assetCompleteness": None,
            "semanticCompleteness": None,
            "interactionReliability": None,
            "accessibility": None,
            "performance": None,
            "visualQuality": 98,
            "variantDiversity": None,
        }
    )
    assert report["gates"]["evidenceSafety"] is None
    assert "evidenceSafety" not in report["hardFailures"]
    assert report["publishable"] is True


def test_shadow_rollout_never_allows_publication_and_rolls_back_on_latency() -> None:
    decision = rollout_decision("synthetic-lead", 100, metrics={"totalRuns": 20, "p95LatencySeconds": 121}, latency_budget_seconds=120)
    assert decision["rollback"] is True
    assert not publish_allowed(rollout_decision("synthetic-lead", 100), shadow_mode=True)
