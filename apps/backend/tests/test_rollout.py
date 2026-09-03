from app.core.rollout import (
    enhanced_html_enabled,
    rollout_bucket,
    rollout_decision,
    should_rollback,
)


def test_rollout_is_deterministic_and_bounded() -> None:
    assert rollout_bucket("lead-1") == rollout_bucket("lead-1")
    assert not enhanced_html_enabled("lead-1", 0)
    assert enhanced_html_enabled("lead-1", 100)


def test_rollout_rollback_requires_enough_observations() -> None:
    assert not should_rollback({"totalRuns": 19, "hardFailures": 19})
    assert should_rollback({"totalRuns": 20, "hardFailures": 2}, failure_threshold=0.05)


def test_rollout_decision_is_auditable_and_holds_on_regression() -> None:
    decision = rollout_decision(
        "lead-1", 100, metrics={"totalRuns": 20, "hardFailures": 2}
    )
    assert decision["enabled"] is False
    assert decision["rollback"] is True
    assert "quality_or_performance_regression" in decision["reasons"]
