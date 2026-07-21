import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from decrochage.api import create_app
from decrochage.serving import ModelBundle


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.full(len(X), 0.7)
        return np.column_stack([1 - proba, proba])


def test_health_and_ready_when_model_missing(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    client = TestClient(create_app())

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 503


def test_predict_with_injected_bundle(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    app = create_app()
    app.state.bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
        catalogue=pd.DataFrame({"filiere": ["Informatique"]}),
    )
    app.state.load_error = None
    client = TestClient(app)

    response = client.post(
        "/predict",
        json={
            "records": [
                {
                    "filiere": "Informatique",
                    "nb_devoirs_total": 10,
                    "nb_devoirs_rendus": 6,
                    "connexions_lms_30j": 4,
                    "heures_lms_total": 2,
                    "ressources_consultees": 8,
                    "commentaire_tuteur": "",
                    "date_inscription": "2024-09-01",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {"predictions": [{"proba_abandon": 0.7, "alerte": 1}]}


def test_predict_requires_api_key_when_configured(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    monkeypatch.setenv("DECROCHAGE_API_KEY", "secret")
    app = create_app()
    app.state.bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
        catalogue=pd.DataFrame({"filiere": ["Informatique"]}),
    )
    client = TestClient(app)

    response = client.post("/predict", json={"records": [{"filiere": "Informatique"}]})

    assert response.status_code == 401


def test_metrics_endpoint_is_exposed(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_admin_reload_requires_key_and_replaces_bundle(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    monkeypatch.setenv("DECROCHAGE_API_KEY", "secret")
    app = create_app()
    replacement = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
    )
    monkeypatch.setattr(
        "decrochage.api.load_configured_bundle",
        lambda: (replacement, None, "2", "models:/decrochage-l1@production"),
    )
    client = TestClient(app)

    unauthorized = client.post("/admin/reload")
    response = client.post("/admin/reload", headers={"X-API-Key": "secret"})

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["model_version"] == "2"
    assert app.state.bundle is replacement
