from app.core.site_quality_metrics import build_quality_gate_report


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
