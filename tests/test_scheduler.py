from dataclasses import replace
from datetime import date, datetime, timezone
import json
from pathlib import Path

from decrochage.scheduler import (
    SchedulerSettings,
    build_scheduler,
    run_monitoring_cycle,
    run_retraining_cycle,
    scheduler_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> SchedulerSettings:
    return SchedulerSettings(
        reference_csv=ROOT / "data/raw/decrochage_etudiants_complet_V5.csv",
        current_csv=ROOT / "data/raw/decrochage_etudiants_echantillon_V5.csv",
        students_csv=ROOT / "data/raw/decrochage_etudiants_complet_V5.csv",
        catalogue_csv=ROOT / "data/raw/catalogue_formations_V5.csv",
        drift_report_path=tmp_path / "drift.json",
        bundle_path=tmp_path / "model.joblib",
        state_path=tmp_path / "state.json",
        trained_on=date(2024, 9, 1),
    )


def test_scheduler_registers_monitoring_and_retraining_jobs(tmp_path: Path) -> None:
    scheduler = build_scheduler(_settings(tmp_path))

    assert {job.id for job in scheduler.get_jobs()} == {"monitoring", "retraining"}


def test_scheduler_manifest_is_json_serializable(tmp_path: Path) -> None:
    manifest = scheduler_manifest(_settings(tmp_path))

    payload = json.dumps({"status": "starting", **manifest})

    assert '"trained_on": "2024-09-01"' in payload


def test_monitoring_cycle_is_idempotent_for_one_day(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    now = datetime(2026, 7, 21, 8, tzinfo=timezone.utc)

    first = run_monitoring_cycle(settings, now=now)
    second = run_monitoring_cycle(settings, now=now)

    assert first["status"] == "succeeded"
    assert settings.drift_report_path.exists()
    assert second == {
        "job": "monitoring",
        "status": "skipped",
        "reason": "already_succeeded_today",
    }


def test_retraining_waits_for_fresh_labels(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.drift_report_path.write_text(
        json.dumps({"summary": {"status": "alert"}, "features": []}),
        encoding="utf-8",
    )

    result = run_retraining_cycle(
        settings,
        now=datetime(2026, 7, 21, 8, tzinfo=timezone.utc),
    )

    assert result["status"] == "succeeded"
    assert result["decision"]["action"] == "investigate_and_collect_labels"
    assert result["decision"]["should_train_candidate"] is False


def test_monitoring_success_is_persisted_when_webhook_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    settings = replace(_settings(tmp_path), alert_webhook_url="https://alerts.invalid")

    def unavailable_webhook(*_args, **_kwargs) -> None:
        raise OSError("offline")

    monkeypatch.setattr("decrochage.scheduler.post_alert_webhook", unavailable_webhook)

    result = run_monitoring_cycle(
        settings,
        now=datetime(2026, 7, 21, 8, tzinfo=timezone.utc),
    )

    assert result["status"] == "succeeded"
    state = json.loads(settings.state_path.read_text(encoding="utf-8"))
    assert state["jobs"]["monitoring"]["last_success_day"] == "2026-07-21"
