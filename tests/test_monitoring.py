import pandas as pd

from decrochage.monitoring import build_drift_report, population_stability_index


def test_population_stability_index_is_zero_for_same_distribution() -> None:
    series = pd.Series([1, 2, 3, 4, 5, 6])

    assert population_stability_index(series, series) == 0.0


def test_build_drift_report_flags_shifted_numeric_feature() -> None:
    reference = pd.DataFrame({"presence": [70, 72, 73, 74, 75, 76, 77, 78]})
    current = pd.DataFrame({"presence": [20, 21, 22, 23, 24, 25, 26, 27]})

    report = build_drift_report(reference, current, feature_cols=["presence"])

    assert report["summary"]["features_checked"] == 1
    assert report["summary"]["status"] in {"watch", "alert"}
    assert report["features"][0]["feature"] == "presence"
