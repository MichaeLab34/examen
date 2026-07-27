import time

import pandas as pd
import pytest

from decrochage.ecodesign import (
    build_arbitrage_table,
    cost_per_metric_point,
    summarize_runs,
    track_emissions,
)


def test_track_emissions_always_measures_duration() -> None:
    with track_emissions("test") as run:
        time.sleep(0.01)
        run["auc"] = 0.9

    assert run["label"] == "test"
    assert run["duree_s"] is not None and run["duree_s"] >= 0.01
    assert run["auc"] == 0.9


def test_summarize_runs_converts_kilograms_to_grams() -> None:
    runs = [{"label": "m", "duree_s": 2.0, "energie_kwh": 0.001, "emissions_kg": 0.002, "auc": 0.9}]

    summary = summarize_runs(runs)

    assert summary.loc[0, "gCO2eq"] == pytest.approx(2.0)
    assert summary.loc[0, "Modèle"] == "m"


def test_summarize_runs_keeps_none_when_tracker_unavailable() -> None:
    runs = [{"label": "m", "duree_s": 2.0, "energie_kwh": None, "emissions_kg": None, "auc": 0.9}]

    summary = summarize_runs(runs)

    assert summary.loc[0, "gCO2eq"] is None
    assert summary.loc[0, "Durée entraînement (s)"] == 2.0


def test_cost_per_metric_point_is_infinite_without_gain() -> None:
    assert cost_per_metric_point(0.90, 0.91, 100.0, 1.0) == float("inf")
    assert cost_per_metric_point(0.90, 0.90, 100.0, 1.0) == float("inf")


def test_cost_per_metric_point_divides_extra_cost_by_gain() -> None:
    assert cost_per_metric_point(0.92, 0.90, 11.0, 1.0) == pytest.approx(500.0)


def test_build_arbitrage_table_compares_against_reference_model() -> None:
    summary = pd.DataFrame(
        {
            "Modèle": ["Régression logistique", "XGBoost"],
            "Durée entraînement (s)": [1.0, 10.0],
            "auc": [0.950, 0.951],
        }
    )

    table = build_arbitrage_table(summary, reference_model="Régression logistique")

    xgb = table.loc[table["Modèle"] == "XGBoost"].iloc[0]
    assert xgb["Surcoût calcul (x)"] == pytest.approx(10.0)
    assert xgb["Gain auc"] == pytest.approx(0.001)
    assert xgb["Coût / point auc"] == pytest.approx(9000.0)


def test_build_arbitrage_table_rejects_unknown_reference() -> None:
    summary = pd.DataFrame({"Modèle": ["A"], "Durée entraînement (s)": [1.0], "auc": [0.9]})

    with pytest.raises(ValueError, match="référence"):
        build_arbitrage_table(summary, reference_model="B")
