import numpy as np

from decrochage.training import select_threshold_by_cost


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
