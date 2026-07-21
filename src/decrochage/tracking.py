"""MLflow experiment tracking for reproducible model training."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Mapping

from .registry import DEFAULT_MLFLOW_URI, configure_registry_uri
from .training import TrainingResult


@dataclass(frozen=True)
class TrackingRun:
    """Identifiers and locations produced by one MLflow tracking run."""

    run_id: str
    experiment_id: str
    artifact_uri: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _scalar_metrics(metrics: Mapping[str, Any]) -> dict[str, float]:
    tracked: dict[str, float] = {}
    for key, value in metrics.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            tracked[key] = float(value)
    return tracked


def _run_parameters(result: TrainingResult) -> dict[str, str | int | float]:
    metrics = result.metrics
    best_params = metrics.get("best_params", {})
    cost_fn, cost_fp = metrics.get("cost_fn_fp", [5.0, 1.0])
    return {
        "model_family": "logistic_regression",
        "class_weight": "balanced",
        "cv_strategy": "stratified_kfold_5",
        "threshold_selection": str(metrics.get("threshold_selection", "unknown")),
        "best_clf_C": float(best_params.get("clf__C", 0.0)),
        "cost_false_negative": float(cost_fn),
        "cost_false_positive": float(cost_fp),
        "feature_count": int(metrics.get("n_features", 0)),
    }


def track_training_result(
    result: TrainingResult,
    *,
    tracking_uri: str | None = None,
    experiment_name: str = "decrochage-l1-training",
    run_name: str | None = None,
    tags: Mapping[str, str] | None = None,
) -> TrackingRun:
    """Log parameters, scalar metrics and reproducibility artifacts to MLflow."""

    import mlflow

    effective_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI") or DEFAULT_MLFLOW_URI
    configure_registry_uri(effective_uri)
    if (
        effective_uri.startswith("sqlite:")
        and mlflow.get_experiment_by_name(experiment_name) is None
    ):
        artifact_root = Path(
            os.getenv("MLFLOW_ARTIFACT_ROOT", "artifacts/mlflow-artifacts")
        ).resolve()
        artifact_root.mkdir(parents=True, exist_ok=True)
        mlflow.create_experiment(
            experiment_name,
            artifact_location=(artifact_root / experiment_name).as_uri(),
        )
    mlflow.set_experiment(experiment_name)
    effective_name = run_name or f"training-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    effective_tags = {
        "project": "decrochage-l1",
        "stage": "candidate-training",
        "decision_mode": "human-promotion-required",
        **(tags or {}),
    }

    with mlflow.start_run(run_name=effective_name, tags=effective_tags) as active_run:
        mlflow.log_params(_run_parameters(result))
        mlflow.log_metrics(_scalar_metrics(result.metrics))
        mlflow.log_dict(result.metrics, "reports/training_metrics.json")
        if result.output_path is not None:
            bundle_path = Path(result.output_path)
            if bundle_path.exists():
                mlflow.log_artifact(str(bundle_path), artifact_path="model_bundle")

        run = mlflow.get_run(active_run.info.run_id)
        return TrackingRun(
            run_id=active_run.info.run_id,
            experiment_id=active_run.info.experiment_id,
            artifact_uri=run.info.artifact_uri,
        )
