import numpy as np
import pandas as pd

from decrochage.training import build_gold_dataset, select_threshold_by_cost, subgroup_recall_gap


def test_select_threshold_by_cost_prefers_recall_when_fn_is_expensive() -> None:
    y_true = np.array([0, 0, 1, 1])
    proba = np.array([0.1, 0.4, 0.45, 0.9])

    threshold, stats = select_threshold_by_cost(
        y_true,
        proba,
        cost_fn=5,
        cost_fp=1,
        thresholds=np.array([0.3, 0.5]),
    )

    assert threshold == 0.3
    assert stats["fn"] == 0
    assert stats["recall"] == 1.0


def test_build_gold_dataset_adds_canonical_split_set() -> None:
    prepared = pd.DataFrame(
        {
            "taux_presence_pct": [90, 40, 85, 35, 75, 30],
            "abandon": [0, 1, 0, 1, 0, 1],
            "moyenne_finale": [14, 6, 13, 5, 12, 4],
        }
    )

    gold_dataset, feature_cols = build_gold_dataset(
        prepared,
        random_state=42,
        allow_fallback=True,
    )

    assert feature_cols == ["taux_presence_pct"]
    assert "split_set" in gold_dataset.columns
    assert set(gold_dataset["split_set"]) <= {"train", "validation", "test"}


def test_subgroup_recall_gap_returns_largest_monitored_gap() -> None:
    X = pd.DataFrame({"sexe": ["F", "F", "M", "M"], "boursier": [1, 0, 1, 0]})
    y_true = pd.Series([1, 1, 1, 1])
    y_pred = np.array([1, 1, 1, 0])

    gap, details = subgroup_recall_gap(X, y_true, y_pred)

    assert gap == 0.5
    assert details["sexe"] == {"F": 1.0, "M": 0.5}


def test_train_model_stamps_the_bundle_with_a_traceable_version() -> None:
    """A score must always be attributable to a specific model.

    `persistence.persist_predictions` reads `model_version` then `trained_at`
    from the bundle metadata. When neither exists, `gold_prediction.model_version`
    stays NULL and the portal can only show "non renseigné" — a decision nobody
    can trace back to a model.
    """
    from datetime import datetime

    from conftest import catalogue_rows, student_rows
    from decrochage.training import train_model

    students = student_rows(120)
    result = train_model(students, catalogue_rows())
    metadata = result.bundle.metadata

    assert metadata["model_version"].startswith("local-")
    # The prefix keeps a local build from passing for a promoted registry
    # version, which is numeric and assigned by MLflow.
    assert not metadata["model_version"].lstrip("local-").isdigit()
    parsed = datetime.fromisoformat(metadata["trained_at"])
    assert parsed.tzinfo is not None
