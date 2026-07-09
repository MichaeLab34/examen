from pathlib import Path

import numpy as np
import pandas as pd

from decrochage.serving import ModelBundle, load_bundle, predict_proba_abandon, save_bundle


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.where(X["taux_rendu_devoirs"].fillna(0) >= 0.5, 0.2, 0.8)
        return np.column_stack([1 - proba, proba])


def _raw_records() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "filiere": "Informatique",
                "nb_devoirs_total": 10,
                "nb_devoirs_rendus": 9,
                "connexions_lms_30j": 10,
                "heures_lms_total": 20,
                "ressources_consultees": 30,
                "commentaire_tuteur": "",
                "date_inscription": "2024-09-01",
            },
            {
                "filiere": "Informatique",
                "nb_devoirs_total": 10,
                "nb_devoirs_rendus": 2,
                "connexions_lms_30j": 2,
                "heures_lms_total": 1,
                "ressources_consultees": 3,
                "commentaire_tuteur": "Signalement",
                "date_inscription": "2024-09-03",
            },
        ]
    )


def test_bundle_reload_and_prediction_contract(tmp_path: Path) -> None:
    catalogue = pd.DataFrame({"filiere": ["Informatique"], "faculte": ["Sciences"]})
    bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
        catalogue=catalogue,
    )

    path = save_bundle(bundle, tmp_path / "bundle.joblib")
    loaded = load_bundle(path)
    scored = predict_proba_abandon(loaded, _raw_records())

    assert scored.columns.tolist() == ["proba_abandon", "alerte"]
    assert scored["proba_abandon"].between(0, 1).all()
    assert scored["alerte"].tolist() == [0, 1]
