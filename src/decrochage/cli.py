"""Command-line interface for the dropout-risk project."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer

from . import features as F
from .monitoring import build_drift_report, write_drift_report
from .persistence import (
    DATABASE_URL_ENV,
    initialize_database,
    make_session_factory,
    persist_drift_report,
    persist_medallion_layers,
    persist_predictions,
    redacted_database_url,
)
from .preprocessing import clean_raw
from .serving import load_bundle, predict_proba_abandon
from .training import prepare_training_frame, train_model

app = typer.Typer(help="Industrialized commands for the decrochage project.")


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


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
        result = persist_medallion_layers(
            session,
            raw_df,
            catalogue_df,
            source_name="csv",
            source_uri=f"{students}:{catalogue}",
        )
    typer.echo(json.dumps(result.__dict__, indent=2, ensure_ascii=False))


@app.command("check-data")
def check_data(
    students: Annotated[Path, typer.Argument(help="Raw student CSV path")],
    catalogue: Annotated[Path, typer.Argument(help="Catalogue CSV path")],
) -> None:
    """Check raw data quality and scoring feature safety."""
    raw_df = _read_csv(students)
    catalogue_df = _read_csv(catalogue)
    prepared = prepare_training_frame(raw_df, catalogue_df)
    feature_cols = F.scoring_feature_columns(prepared)
    F.assert_no_leakage(feature_cols)
    join_cols = [col for col in catalogue_df.columns if col != "filiere"]
    join_coverage = prepared[join_cols].notna().any(axis=1).mean() if join_cols else float("nan")
    report = {
        "rows_raw": int(len(raw_df)),
        "duplicates_raw": int(raw_df.duplicated().sum()),
        "rows_after_cleaning": int(len(prepared)),
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
) -> None:
    """Train a model bundle with train/validation/test separation."""
    result = train_model(_read_csv(students), _read_csv(catalogue), output_path=output)
    payload = {"model_path": str(result.output_path), "metrics": result.metrics}
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


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "0.0.0.0",
    port: Annotated[int, typer.Option(help="Bind port")] = 8000,
) -> None:
    """Run the FastAPI inference service."""
    import uvicorn

    uvicorn.run("decrochage.api:app", host=host, port=port, reload=False)
