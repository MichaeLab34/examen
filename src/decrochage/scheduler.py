"""Scheduled monitoring and candidate retraining workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .alerting import (
    AlertEventSnapshot,
    evaluate_drift_alert,
    ping_dead_mans_switch,
    post_alert_webhook,
)
from .logging_config import configure_json_logger
from .monitoring import build_drift_report, write_drift_report
from .operations import decide_retraining
from .preprocessing import clean_raw
from .registry import register_saved_bundle
from .tracking import track_training_result
from .training import train_model

LOGGER = configure_json_logger("decrochage.scheduler")


@dataclass(frozen=True)
class SchedulerSettings:
    """Environment-backed paths and policies used by scheduled jobs."""

    reference_csv: Path = Path("data/raw/decrochage_etudiants_complet_V5.csv")
    current_csv: Path = Path("data/raw/decrochage_etudiants_echantillon_V5.csv")
    students_csv: Path = Path("data/raw/decrochage_etudiants_complet_V5.csv")
    catalogue_csv: Path = Path("data/raw/catalogue_formations_V5.csv")
    drift_report_path: Path = Path("reports/drift_report.json")
    bundle_path: Path = Path("artifacts/models/model_bundle.joblib")
    state_path: Path = Path("artifacts/scheduler/state.json")
    trained_on: date = date(2024, 9, 1)
    labels_available: bool = False
    performance_alert: bool = False
    monitor_cron: str = "0 6 * * 1"
    retrain_cron: str = "0 7 * * 1"
    timezone_name: str = "Europe/Paris"
    heartbeat_url: str | None = None
    alert_webhook_url: str | None = None
    tracking_uri: str | None = None
    experiment_name: str = "decrochage-l1-training"
    registered_model: str = "decrochage-l1"

    @classmethod
    def from_env(cls) -> SchedulerSettings:
        return cls(
            reference_csv=Path(
                os.getenv(
                    "DECROCHAGE_REFERENCE_CSV",
                    "data/raw/decrochage_etudiants_complet_V5.csv",
                )
            ),
            current_csv=Path(
                os.getenv(
                    "DECROCHAGE_CURRENT_CSV",
                    "data/raw/decrochage_etudiants_echantillon_V5.csv",
                )
            ),
            students_csv=Path(
                os.getenv(
                    "DECROCHAGE_STUDENTS_CSV",
                    "data/raw/decrochage_etudiants_complet_V5.csv",
                )
            ),
            catalogue_csv=Path(
                os.getenv("DECROCHAGE_CATALOGUE_CSV", "data/raw/catalogue_formations_V5.csv")
            ),
            drift_report_path=Path(
                os.getenv("DECROCHAGE_DRIFT_REPORT_PATH", "reports/drift_report.json")
            ),
            bundle_path=Path(
                os.getenv("DECROCHAGE_MODEL_PATH", "artifacts/models/model_bundle.joblib")
            ),
            state_path=Path(
                os.getenv("DECROCHAGE_SCHEDULER_STATE", "artifacts/scheduler/state.json")
            ),
            trained_on=date.fromisoformat(os.getenv("DECROCHAGE_TRAINED_ON", "2024-09-01")),
            labels_available=_env_bool("DECROCHAGE_LABELS_AVAILABLE"),
            performance_alert=_env_bool("DECROCHAGE_PERFORMANCE_ALERT"),
            monitor_cron=os.getenv("DECROCHAGE_MONITOR_CRON", "0 6 * * 1"),
            retrain_cron=os.getenv("DECROCHAGE_RETRAIN_CRON", "0 7 * * 1"),
            timezone_name=os.getenv("DECROCHAGE_SCHEDULER_TIMEZONE", "Europe/Paris"),
            heartbeat_url=os.getenv("DECROCHAGE_HEALTHCHECK_URL") or None,
            alert_webhook_url=os.getenv("DECROCHAGE_ALERT_WEBHOOK_URL") or None,
            tracking_uri=os.getenv("MLFLOW_TRACKING_URI") or None,
            experiment_name=os.getenv("MLFLOW_EXPERIMENT_NAME", "decrochage-l1-training"),
            registered_model=os.getenv("DECROCHAGE_REGISTERED_MODEL", "decrochage-l1"),
        )


def _env_bool(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in {"1", "true", "yes", "on"}


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    temporary.replace(path)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def _notify(settings: SchedulerSettings, payload: dict[str, Any]) -> None:
    if settings.alert_webhook_url:
        try:
            post_alert_webhook(settings.alert_webhook_url, payload)
        except Exception:  # Notification failure must not duplicate a completed model job.
            LOGGER.exception("Operational webhook delivery failed")


def _heartbeat(settings: SchedulerSettings, *, success: bool) -> None:
    if settings.heartbeat_url:
        try:
            ping_dead_mans_switch(settings.heartbeat_url, success=success)
        except Exception:  # The external dead-man's switch detects this missing ping.
            LOGGER.exception("External heartbeat delivery failed")


def _execute_once_per_day(
    job_name: str,
    settings: SchedulerSettings,
    action: Callable[[], dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run one job at most once per UTC day and persist its outcome atomically."""

    current = now or datetime.now(timezone.utc)
    state = _read_state(settings.state_path)
    day_key = current.date().isoformat()
    if state.get("jobs", {}).get(job_name, {}).get("last_success_day") == day_key:
        return {"job": job_name, "status": "skipped", "reason": "already_succeeded_today"}

    try:
        payload = action()
        state = _read_state(settings.state_path)
        jobs = state.setdefault("jobs", {})
        jobs[job_name] = {
            "last_success_day": day_key,
            "last_success_at": current.isoformat(),
            "result": payload,
        }
        _write_state(settings.state_path, state)
        _heartbeat(settings, success=True)
        return {"job": job_name, "status": "succeeded", **payload}
    except Exception:
        _heartbeat(settings, success=False)
        raise


def run_monitoring_cycle(
    settings: SchedulerSettings,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compute drift, apply alert hysteresis and emit an operational heartbeat."""

    current = now or datetime.now(timezone.utc)

    def action() -> dict[str, Any]:
        reference = clean_raw(_read_csv(settings.reference_csv))
        observed = clean_raw(_read_csv(settings.current_csv))
        report = build_drift_report(reference, observed)
        write_drift_report(report, settings.drift_report_path)

        state = _read_state(settings.state_path)
        alert_state = state.get("drift_alert", {})
        last_event = None
        if alert_state.get("triggered_at"):
            last_event = AlertEventSnapshot(
                triggered_at=datetime.fromisoformat(alert_state["triggered_at"]),
                resolved_at=(
                    datetime.fromisoformat(alert_state["resolved_at"])
                    if alert_state.get("resolved_at")
                    else None
                ),
            )
        decision = evaluate_drift_alert(report, now=current, last_event=last_event)
        if decision.should_alert:
            _notify(settings, {"event": "drift_alert", **decision.to_dict()})
            state["drift_alert"] = {"triggered_at": current.isoformat(), "resolved_at": None}
        elif decision.should_resolve:
            _notify(settings, {"event": "drift_resolved", **decision.to_dict()})
            state["drift_alert"] = {
                **alert_state,
                "resolved_at": current.isoformat(),
            }
        _write_state(settings.state_path, state)
        return {
            "report_path": str(settings.drift_report_path),
            "drift_status": report.get("summary", {}).get("status", "missing"),
            "alert": decision.to_dict(),
        }

    return _execute_once_per_day("monitoring", settings, action, now=current)


def run_retraining_cycle(
    settings: SchedulerSettings,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate retraining and, when justified, register a new candidate."""

    current = now or datetime.now(timezone.utc)

    def action() -> dict[str, Any]:
        if not settings.drift_report_path.exists():
            raise FileNotFoundError(
                f"Missing drift report: {settings.drift_report_path}; run monitoring first"
            )
        report = json.loads(settings.drift_report_path.read_text(encoding="utf-8"))
        state = _read_state(settings.state_path)
        trained_on = date.fromisoformat(
            state.get("last_trained_on", settings.trained_on.isoformat())
        )
        decision = decide_retraining(
            report,
            trained_on=trained_on,
            as_of=current.date(),
            labels_available=settings.labels_available,
            performance_alert=settings.performance_alert,
        )
        payload: dict[str, Any] = {"decision": decision.to_dict()}
        if not decision.should_train_candidate:
            return payload

        result = train_model(
            _read_csv(settings.students_csv),
            _read_csv(settings.catalogue_csv),
            output_path=settings.bundle_path,
        )
        tracking_run = track_training_result(
            result,
            tracking_uri=settings.tracking_uri,
            experiment_name=settings.experiment_name,
            tags={"trigger": ",".join(decision.reasons)},
        )
        version = register_saved_bundle(
            settings.bundle_path,
            settings.registered_model,
            run_id=tracking_run.run_id,
            uri=settings.tracking_uri,
        )
        state = _read_state(settings.state_path)
        state["last_trained_on"] = current.date().isoformat()
        _write_state(settings.state_path, state)
        payload.update(
            {
                "candidate_version": version,
                "tracking": tracking_run.to_dict(),
                "promotion": "human_approval_required",
            }
        )
        _notify(
            settings,
            {
                "event": "candidate_ready_for_review",
                "model": settings.registered_model,
                **payload,
            },
        )
        return payload

    return _execute_once_per_day("retraining", settings, action, now=current)


def build_scheduler(settings: SchedulerSettings) -> BlockingScheduler:
    """Build the standalone scheduler used by the Compose Run profile."""

    scheduler = BlockingScheduler(timezone=settings.timezone_name)
    scheduler.add_job(
        run_monitoring_cycle,
        CronTrigger.from_crontab(settings.monitor_cron, timezone=settings.timezone_name),
        kwargs={"settings": settings},
        id="monitoring",
        name="Weekly data-drift monitoring",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=3600,
        replace_existing=True,
    )
    scheduler.add_job(
        run_retraining_cycle,
        CronTrigger.from_crontab(settings.retrain_cron, timezone=settings.timezone_name),
        kwargs={"settings": settings},
        id="retraining",
        name="Weekly retraining-policy evaluation",
        coalesce=True,
        max_instances=1,
        misfire_grace_time=86400,
        replace_existing=True,
    )
    return scheduler


def scheduler_manifest(settings: SchedulerSettings) -> dict[str, Any]:
    """Return a redacted, serializable view of the active schedule."""

    manifest = asdict(settings)
    for key, value in list(manifest.items()):
        if isinstance(value, (Path, date, datetime)):
            manifest[key] = str(value)
    manifest["heartbeat_url"] = "configured" if settings.heartbeat_url else "disabled"
    manifest["alert_webhook_url"] = "configured" if settings.alert_webhook_url else "disabled"
    manifest["tracking_uri"] = "configured" if settings.tracking_uri else "local_sqlite"
    return manifest
