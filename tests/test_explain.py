"""Exactness of the analytical explanation used by the portal (ADR-4).

The point of these tests is the additive invariant: for a logistic regression,
`intercept + sum(coef * x)` IS the model log-odds. If that ever stops holding,
the risk sheet is showing numbers that do not describe the decision.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from decrochage import features as F
from decrochage.portal.labels import format_value, humanize_feature
from decrochage.serving import (
    ModelBundle,
    can_explain,
    explain_prediction,
    prepare_features,
)

from conftest import build_linear_bundle, catalogue_rows, student_rows


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.full(len(X), 0.7)
        return np.column_stack([1 - proba, proba])


@pytest.fixture
def bundle() -> ModelBundle:
    return build_linear_bundle(student_rows(), catalogue_rows())


@pytest.fixture
def gold_features(bundle: ModelBundle) -> pd.DataFrame:
    return prepare_features(student_rows(), bundle.feature_cols, bundle.catalogue)


def test_contributions_sum_to_the_model_log_odds(
    bundle: ModelBundle, gold_features: pd.DataFrame
) -> None:
    for row in (0, 3, 7):
        explanation = explain_prediction(bundle, gold_features, row=row)
        expected_log_odds = float(bundle.pipeline.decision_function(gold_features.iloc[[row]])[0])

        total = explanation.intercept + sum(item.contribution for item in explanation.contributions)

        assert explanation.log_odds == pytest.approx(expected_log_odds, abs=1e-9)
        assert total == pytest.approx(expected_log_odds, abs=1e-9)


def test_explained_probability_matches_the_pipeline(
    bundle: ModelBundle, gold_features: pd.DataFrame
) -> None:
    explanation = explain_prediction(bundle, gold_features, row=2)
    expected = float(bundle.pipeline.predict_proba(gold_features.iloc[[2]])[0, 1])

    assert explanation.proba == pytest.approx(expected, abs=1e-9)


def test_factors_are_split_by_direction_and_capped(
    bundle: ModelBundle, gold_features: pd.DataFrame
) -> None:
    explanation = explain_prediction(bundle, gold_features, row=0, top_n=3)

    risk = explanation.risk_factors()
    protective = explanation.protective_factors()

    assert len(risk) <= 3
    assert len(protective) <= 3
    assert all(item.contribution > 0 for item in risk)
    assert all(item.contribution < 0 for item in protective)
    assert all(item.direction == "aggravant" for item in risk)
    assert all(item.direction == "protecteur" for item in protective)
    # Sorted by decreasing magnitude within each direction.
    assert [abs(item.contribution) for item in risk] == sorted(
        (abs(item.contribution) for item in risk), reverse=True
    )


def test_explanation_never_references_excluded_columns(
    bundle: ModelBundle, gold_features: pd.DataFrame
) -> None:
    explanation = explain_prediction(bundle, gold_features, row=1)
    names = " ".join(item.name for item in explanation.contributions)

    forbidden = F.LEAKAGE_TARGET_COLS + F.LEAKAGE_TEMPORAL_COLS + F.ID_COLS + F.LEURRE_COLS
    for column in forbidden:
        assert column not in names


def test_non_linear_bundle_is_rejected_explicitly() -> None:
    bundle = ModelBundle(pipeline=DummyPipeline(), feature_cols=["age"], threshold=0.5)

    assert can_explain(bundle) is False
    with pytest.raises(ValueError, match="linear pre/clf pipeline"):
        explain_prediction(bundle, pd.DataFrame({"age": [20]}))


def test_out_of_range_row_is_rejected(bundle: ModelBundle, gold_features: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="out of range"):
        explain_prediction(bundle, gold_features, row=len(gold_features))

    with pytest.raises(ValueError, match="at least one row"):
        explain_prediction(bundle, gold_features.iloc[0:0])


def test_transformed_feature_names_become_business_labels() -> None:
    assert humanize_feature("num__taux_rendu_devoirs") == "taux de rendu des devoirs"
    assert humanize_feature("cat__filiere_Informatique") == "filière : Informatique"
    assert humanize_feature("num__variable_inconnue_du_dictionnaire") == (
        "variable inconnue du dictionnaire"
    )


def test_values_are_formatted_for_a_non_technical_reader() -> None:
    assert format_value("num__taux_rendu_devoirs", 0.42) == "42 %"
    assert format_value("num__taux_presence_pct", 87.0) == "87 %"
    assert format_value("num__connexions_lms_30j", 12.0) == "12"
    assert format_value("num__age", float("nan")) == "non renseigné"
    assert format_value("cat__filiere_Gestion", None) == "non renseigné"
