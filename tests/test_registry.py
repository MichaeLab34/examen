from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from decrochage.registry import (
    load_bundle_by_alias,
    promote_candidate,
    register_bundle,
    rollback_production,
    version_at,
)
from decrochage.serving import ModelBundle, save_bundle


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.full(len(X), 0.7)
        return np.column_stack([1 - proba, proba])


def _bundle(path: Path, recall: float) -> Path:
    bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_presence_pct"],
        threshold=0.5,
        metadata={
            "auc_test": 0.95,
            "recall_test": recall,
            "fairness_recall_gap_test": 0.04,
        },
    )
    return save_bundle(bundle, path)


def test_registry_candidate_promotion_and_rollback(tmp_path: Path) -> None:
    uri = f"sqlite:///{tmp_path.as_posix()}/mlflow.db"
    name = "decrochage-test-model"

    v1_path = _bundle(tmp_path / "v1.joblib", recall=0.95)
    v1 = register_bundle(
        v1_path,
        name,
        metrics={
            "auc_test": 0.95,
            "recall_test": 0.95,
            "fairness_recall_gap_test": 0.04,
        },
        uri=uri,
    )
    assert promote_candidate(name, v1, human_approved=True, uri=uri).approved_for_production

    v2_path = _bundle(tmp_path / "v2.joblib", recall=0.96)
    v2 = register_bundle(
        v2_path,
        name,
        metrics={
            "auc_test": 0.96,
            "recall_test": 0.96,
            "fairness_recall_gap_test": 0.03,
        },
        uri=uri,
    )
    assert promote_candidate(name, v2, human_approved=True, uri=uri).approved_for_production
    assert int(version_at(name, "production", uri=uri).version) == v2

    loaded, version = load_bundle_by_alias(name, uri=uri)
    assert version == str(v2)
    assert loaded.metadata["recall_test"] == 0.96

    rollback_production(name, v1, uri=uri)
    assert int(version_at(name, "production", uri=uri).version) == v1


def test_remote_registry_requires_originating_run(tmp_path: Path) -> None:
    bundle_path = _bundle(tmp_path / "remote.joblib", recall=0.95)

    with pytest.raises(ValueError, match="run_id is required"):
        register_bundle(bundle_path, "decrochage-test-model", uri="http://mlflow:5000")
