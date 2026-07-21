from pathlib import Path

import mlflow
from mlflow import MlflowClient

from decrochage.serving import ModelBundle
from decrochage.tracking import track_training_result
from decrochage.training import TrainingResult


def test_training_result_logs_params_metrics_and_artifacts(tmp_path: Path) -> None:
    bundle_path = tmp_path / "model_bundle.joblib"
    bundle_path.write_bytes(b"bundle-proof")
    result = TrainingResult(
        bundle=ModelBundle(pipeline=object(), feature_cols=["engagement"], threshold=0.3),
        metrics={
            "auc_test": 0.91,
            "recall_test": 0.93,
            "threshold": 0.3,
            "n_features": 1,
            "threshold_selection": "validation_cost_minimization",
            "best_params": {"clf__C": 0.5},
            "cost_fn_fp": [5.0, 1.0],
            "subgroup_recall_test": {"sexe": {"F": 0.92, "H": 0.94}},
        },
        output_path=bundle_path,
    )
    tracking_uri = f"sqlite:///{(tmp_path / 'mlflow.db').as_posix()}"
    mlflow.set_tracking_uri(tracking_uri)
    MlflowClient().create_experiment(
        "tracking-test",
        artifact_location=(tmp_path / "mlartifacts").as_uri(),
    )

    tracked = track_training_result(
        result,
        tracking_uri=tracking_uri,
        experiment_name="tracking-test",
        run_name="proof-run",
    )

    mlflow.set_tracking_uri(tracking_uri)
    run = MlflowClient().get_run(tracked.run_id)
    artifact_paths = {
        item.path for item in MlflowClient().list_artifacts(tracked.run_id, "model_bundle")
    }
    report_paths = {item.path for item in MlflowClient().list_artifacts(tracked.run_id, "reports")}
    assert run.data.params["model_family"] == "logistic_regression"
    assert run.data.metrics["auc_test"] == 0.91
    assert "model_bundle/model_bundle.joblib" in artifact_paths
    assert "reports/training_metrics.json" in report_paths
