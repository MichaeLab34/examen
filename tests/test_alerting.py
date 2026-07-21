from datetime import UTC, datetime, timedelta

from decrochage.alerting import AlertEventSnapshot, evaluate_drift_alert

NOW = datetime(2026, 7, 21, 10, 0, tzinfo=UTC)


def _report(status: str, psi: float) -> dict:
    return {
        "summary": {"status": status},
        "features": [{"feature": "taux_presence_pct", "status": status, "psi": psi}],
    }


def test_first_drift_alert_is_sent_then_suppressed_during_cooldown() -> None:
    first = evaluate_drift_alert(_report("alert", 0.4), now=NOW, last_event=None)
    repeated = evaluate_drift_alert(
        _report("alert", 0.4),
        now=NOW + timedelta(hours=1),
        last_event=AlertEventSnapshot(triggered_at=NOW),
    )

    assert first.should_alert is True
    assert first.affected_features == ("taux_presence_pct",)
    assert repeated.should_alert is False


def test_healthy_report_resolves_active_alert() -> None:
    decision = evaluate_drift_alert(
        _report("ok", 0.01),
        now=NOW + timedelta(hours=1),
        last_event=AlertEventSnapshot(triggered_at=NOW),
    )

    assert decision.should_resolve is True
