"""Command-line interface for the dropout-risk project."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from . import features as F
from .alerting import AlertEventSnapshot, evaluate_drift_alert, ping_dead_mans_switch
from .monitoring import build_drift_report, write_drift_report
from .operations import decide_retraining
from .persistence import (
    DATABASE_URL_ENV,
    initialize_database,
    make_session_factory,
    persist_drift_report,
    persist_medallion_layers,
    persist_predictions,
    purge_expired_batches,
    redacted_database_url,
)
from .preprocessing import clean_raw
from .registry import promote_candidate, register_saved_bundle, rollback_production, version_at
from .scheduler import (
    SchedulerSettings,
    build_scheduler,
    run_monitoring_cycle,
    run_retraining_cycle,
    scheduler_manifest,
)
from .serving import load_bundle, predict_proba_abandon
from .tracking import track_training_result
from .training import build_gold_dataset, prepare_training_frame, train_model

app = typer.Typer(help="Industrialized commands for the decrochage project.")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@app.command("init-db")
def init_db(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help=f"SQLAlchemy database URL. Defaults to ${DATABASE_URL_ENV} or local SQLite.",
        ),
    ] = None,
) -> None:
    """Create database tables used by the medallion architecture."""
    initialize_database(database_url)
    typer.echo(
        json.dumps(
            {"database_url": redacted_database_url(database_url), "status": "ready"},
            indent=2,
        )
    )


@app.command("medallion-load")
def medallion_load(
    students: Annotated[Path, typer.Argument(help="Raw student CSV path")],
    catalogue: Annotated[Path, typer.Argument(help="Catalogue CSV path")],
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help=f"SQLAlchemy database URL. Defaults to ${DATABASE_URL_ENV} or local SQLite.",
        ),
    ] = None,
) -> None:
    """Persist CSV inputs into Bronze, Silver and Gold database layers."""
    initialize_database(database_url)
    raw_df = _read_csv(students)
    catalogue_df = _read_csv(catalogue)
    with make_session_factory(database_url).begin() as session:
        try:
            result = persist_medallion_layers(
                session,
                raw_df,
                catalogue_df,
                source_name="csv",
                source_uri=f"{students}:{catalogue}",
                actor="cli",
            )
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))


@app.command("purge-expired")
def purge_expired(
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help=f"SQLAlchemy database URL. Defaults to ${DATABASE_URL_ENV} or local SQLite.",
        ),
    ] = None,
) -> None:
    """Purge expired medallion batches according to the RGPD retention policy."""
    initialize_database(database_url)
    with make_session_factory(database_url).begin() as session:
        purged_batches = purge_expired_batches(session, actor="cli")
    typer.echo(json.dumps({"purged_batches": purged_batches}, indent=2, ensure_ascii=False))


@app.command("check-data")
def check_data(
    students: Annotated[Path, typer.Argument(help="Raw student CSV path")],
    catalogue: Annotated[Path, typer.Argument(help="Catalogue CSV path")],
) -> None:
    """Check raw data quality and scoring feature safety."""
    raw_df = _read_csv(students)
    catalogue_df = _read_csv(catalogue)
    prepared = prepare_training_frame(raw_df, catalogue_df)
    gold_dataset, feature_cols = build_gold_dataset(prepared)
    join_cols = [col for col in catalogue_df.columns if col != "filiere"]
    join_coverage = prepared[join_cols].notna().any(axis=1).mean() if join_cols else float("nan")
    report = {
        "rows_raw": int(len(raw_df)),
        "duplicates_raw": int(raw_df.duplicated().sum()),
        "rows_after_cleaning": int(len(prepared)),
        "rows_gold": int(len(gold_dataset)),
        "abandon_rate": float(prepared[F.TARGET_CLF].mean()),
        "catalogue_join_coverage": float(join_coverage),
        "feature_count": int(len(feature_cols)),
        "leakage_guard": "ok",
    }
    typer.echo(json.dumps(report, indent=2, ensure_ascii=False))


@app.command("train")
def train(
    students: Annotated[Path, typer.Argument(help="Raw student CSV path")],
    catalogue: Annotated[Path, typer.Argument(help="Catalogue CSV path")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output model bundle path"),
    ] = Path("artifacts/models/model_bundle.joblib"),
    track: Annotated[
        bool,
        typer.Option("--track/--no-track", help="Record the run in MLflow Tracking"),
    ] = True,
    experiment_name: Annotated[
        str,
        typer.Option(help="MLflow experiment name"),
    ] = "decrochage-l1-training",
    tracking_uri: Annotated[
        str | None,
        typer.Option(help="MLflow tracking URI; defaults to MLFLOW_TRACKING_URI"),
    ] = None,
) -> None:
    """Train a model bundle and record a reproducible MLflow experiment."""
    result = train_model(_read_csv(students), _read_csv(catalogue), output_path=output)
    payload: dict[str, object] = {
        "model_path": str(result.output_path),
        "metrics": result.metrics,
    }
    if track:
        tracking = track_training_result(
            result,
            tracking_uri=tracking_uri or os.getenv("MLFLOW_TRACKING_URI"),
            experiment_name=experiment_name,
        )
        payload["mlflow"] = tracking.to_dict()
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("predict")
def predict(
    model: Annotated[Path, typer.Argument(help="Model bundle path")],
    input_csv: Annotated[Path, typer.Argument(help="Raw student CSV path")],
    output_csv: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output predictions CSV path"),
    ] = Path("reports/predictions.csv"),
    persist_db: Annotated[
        bool,
        typer.Option("--persist-db", help="Persist predictions into the Gold database table"),
    ] = False,
    batch_id: Annotated[
        str | None,
        typer.Option("--batch-id", help="Existing ingestion batch id for persisted predictions"),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help=f"SQLAlchemy database URL. Defaults to ${DATABASE_URL_ENV} or local SQLite.",
        ),
    ] = None,
) -> None:
    """Score raw student records and write predictions."""
    bundle = load_bundle(model)
    raw_df = _read_csv(input_csv)
    scored = predict_proba_abandon(bundle, raw_df)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_csv, index=False)
    payload: dict[str, str | int] = {"predictions_csv": str(output_csv)}
    if persist_db:
        if batch_id is None:
            raise typer.BadParameter("--batch-id is required when --persist-db is enabled")
        initialize_database(database_url)
        with make_session_factory(database_url).begin() as session:
            try:
                payload["rows_persisted"] = persist_predictions(
                    session, batch_id, raw_df, scored, bundle
                )
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("drift-report")
def drift_report(
    reference_csv: Annotated[Path, typer.Argument(help="Reference CSV path")],
    current_csv: Annotated[Path, typer.Argument(help="Current CSV path")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output JSON report path"),
    ] = Path("reports/drift_report.json"),
    persist_db: Annotated[
        bool,
        typer.Option("--persist-db", help="Persist the drift report into the Gold database table"),
    ] = False,
    batch_id: Annotated[
        str | None,
        typer.Option("--batch-id", help="Existing ingestion batch id for persisted drift report"),
    ] = None,
    database_url: Annotated[
        str | None,
        typer.Option(
            "--database-url",
            help=f"SQLAlchemy database URL. Defaults to ${DATABASE_URL_ENV} or local SQLite.",
        ),
    ] = None,
) -> None:
    """Build a numeric PSI drift report."""
    reference = clean_raw(_read_csv(reference_csv))
    current = clean_raw(_read_csv(current_csv))
    report = build_drift_report(reference, current)
    path = write_drift_report(report, output)
    payload: dict[str, str | int] = {"drift_report": str(path)}
    if persist_db:
        if batch_id is None:
            raise typer.BadParameter("--batch-id is required when --persist-db is enabled")
        initialize_database(database_url)
        with make_session_factory(database_url).begin() as session:
            try:
                payload["drift_report_id"] = persist_drift_report(session, batch_id, report)
            except ValueError as exc:
                raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command("retraining-decision")
def retraining_decision(
    drift_report_json: Annotated[Path, typer.Argument(help="PSI drift report JSON path")],
    trained_on: Annotated[str, typer.Option(help="Current production training date (YYYY-MM-DD)")],
    as_of: Annotated[
        str, typer.Option(help="Decision date (YYYY-MM-DD)")
    ] = date.today().isoformat(),
    labels_available: Annotated[
        bool,
        typer.Option(help="Fresh abandonment labels are available for supervised retraining"),
    ] = False,
    performance_alert: Annotated[
        bool,
        typer.Option(help="Observed AUC/recall crossed its alert threshold"),
    ] = False,
) -> None:
    """Apply the annual-cohort retraining policy to a monitoring report."""

    decision = decide_retraining(
        _read_json(drift_report_json),
        trained_on=date.fromisoformat(trained_on),
        as_of=date.fromisoformat(as_of),
        labels_available=labels_available,
        performance_alert=performance_alert,
    )
    typer.echo(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))


@app.command("alert-decision")
def alert_decision(
    drift_report_json: Annotated[Path, typer.Argument(help="PSI drift report JSON path")],
    last_triggered_at: Annotated[
        str | None,
        typer.Option(help="Last unresolved alert timestamp in ISO-8601 format"),
    ] = None,
    cooldown_hours: Annotated[float, typer.Option(help="Minimum delay before a reminder")] = 24.0,
) -> None:
    """Evaluate drift alert hysteresis and cooldown without sending a notification."""

    last_event = None
    if last_triggered_at:
        parsed = datetime.fromisoformat(last_triggered_at.replace("Z", "+00:00"))
        last_event = AlertEventSnapshot(triggered_at=parsed)
    decision = evaluate_drift_alert(
        _read_json(drift_report_json),
        now=datetime.now(timezone.utc),
        last_event=last_event,
        cooldown=pd.Timedelta(hours=cooldown_hours).to_pytimedelta(),
    )
    typer.echo(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False, default=str))


@app.command("model-register")
def model_register(
    bundle_path: Annotated[Path, typer.Argument(help="Saved joblib bundle path")],
    name: Annotated[str, typer.Option(help="Registered model name")] = "decrochage-l1",
    run_id: Annotated[
        str | None,
        typer.Option(help="MLflow run containing model_bundle/<bundle filename>"),
    ] = None,
    registry_uri: Annotated[
        str | None,
        typer.Option(help="MLflow tracking/registry URI; defaults to MLFLOW_TRACKING_URI"),
    ] = None,
) -> None:
    """Register a trained bundle as the candidate model."""

    version = register_saved_bundle(
        bundle_path,
        name,
        run_id=run_id,
        uri=registry_uri or os.getenv("MLFLOW_TRACKING_URI"),
    )
    typer.echo(json.dumps({"name": name, "version": version, "alias": "candidate"}, indent=2))


@app.command("model-promote")
def model_promote(
    version: Annotated[int, typer.Argument(help="Candidate version to evaluate")],
    name: Annotated[str, typer.Option(help="Registered model name")] = "decrochage-l1",
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Record the required human approval"),
    ] = False,
    registry_uri: Annotated[str | None, typer.Option(help="MLflow tracking/registry URI")] = None,
) -> None:
    """Evaluate and, with explicit approval, promote a candidate to production."""

    decision = promote_candidate(
        name,
        version,
        human_approved=approve,
        uri=registry_uri or os.getenv("MLFLOW_TRACKING_URI"),
    )
    typer.echo(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    if not decision.approved_for_production:
        raise typer.Exit(code=2)


@app.command("model-rollback")
def model_rollback(
    version: Annotated[int, typer.Argument(help="Previous version to restore")],
    name: Annotated[str, typer.Option(help="Registered model name")] = "decrochage-l1",
    registry_uri: Annotated[str | None, typer.Option(help="MLflow tracking/registry URI")] = None,
) -> None:
    """Restore a previous production version by moving the MLflow alias."""

    rollback_production(
        name,
        version,
        uri=registry_uri or os.getenv("MLFLOW_TRACKING_URI"),
    )
    current = version_at(
        name,
        "production",
        uri=registry_uri or os.getenv("MLFLOW_TRACKING_URI"),
    )
    typer.echo(json.dumps({"name": name, "production_version": int(current.version)}, indent=2))


@app.command("heartbeat")
def heartbeat(
    url: Annotated[
        str | None,
        typer.Option(help="healthchecks.io-compatible URL; defaults to DECROCHAGE_HEALTHCHECK_URL"),
    ] = None,
    success: Annotated[
        bool, typer.Option(help="Send a success ping; use --no-success on failure")
    ] = True,
) -> None:
    """Signal that a scheduled scoring, monitoring or retraining job ran."""

    target = url or os.getenv("DECROCHAGE_HEALTHCHECK_URL")
    if not target:
        raise typer.BadParameter("A URL or DECROCHAGE_HEALTHCHECK_URL is required")
    status_code = ping_dead_mans_switch(target, success=success)
    typer.echo(json.dumps({"heartbeat_status": status_code, "success": success}, indent=2))


@app.command("schedule")
def schedule(
    run_once: Annotated[
        str | None,
        typer.Option(help="Run only 'monitoring' or 'retraining', then exit"),
    ] = None,
) -> None:
    """Run the operational scheduler or execute one scheduled cycle."""

    settings = SchedulerSettings.from_env()
    if run_once == "monitoring":
        payload = run_monitoring_cycle(settings)
    elif run_once == "retraining":
        payload = run_retraining_cycle(settings)
    elif run_once is not None:
        raise typer.BadParameter("--run-once must be 'monitoring' or 'retraining'")
    else:
        scheduler = build_scheduler(settings)
        typer.echo(json.dumps({"status": "starting", **scheduler_manifest(settings)}, indent=2))
        scheduler.start()
        return
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Bind port")] = 8000,
) -> None:
    """Run the FastAPI inference service."""
    import uvicorn

    uvicorn.run("decrochage.api:app", host=host, port=port, reload=False)
