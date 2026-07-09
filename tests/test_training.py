import numpy as np
import pandas as pd

from decrochage.training import build_gold_dataset, select_threshold_by_cost


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
