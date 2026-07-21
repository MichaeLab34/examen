from io import StringIO

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from decrochage.api import AUDIT_LOGGER, create_app
from decrochage.serving import ModelBundle


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.full(len(X), 0.7)
        return np.column_stack([1 - proba, proba])


PREDICTION_RECORD = {
    "filiere": "Informatique",
    "nb_devoirs_total": 10,
    "nb_devoirs_rendus": 6,
    "connexions_lms_30j": 4,
    "heures_lms_total": 2,
    "ressources_consultees": 8,
    "commentaire_tuteur": "",
    "date_inscription": "2024-09-01",
}


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


def test_request_id_is_returned_and_logged_without_payload(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    app = create_app()
    app.state.bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
        catalogue=pd.DataFrame({"filiere": ["Informatique"]}),
    )
    client = TestClient(app)

    stream = StringIO()
    handler = next(
        item for item in AUDIT_LOGGER.handlers if getattr(item, "decrochage_json", False)
    )
    previous_stream = handler.setStream(stream)
    try:
        response = client.post(
            "/predict",
            headers={"X-Request-ID": "jury-demo-001"},
            json={"records": [PREDICTION_RECORD]},
        )
    finally:
        handler.setStream(previous_stream)

    log_output = stream.getvalue()
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "jury-demo-001"
    assert '"request_id":"jury-demo-001"' in log_output
    assert '"event":"api_request"' in log_output
    assert '"timestamp":' in log_output
    assert "Informatique" not in log_output


def test_predict_rate_limit_returns_429_and_retry_after(monkeypatch) -> None:
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    monkeypatch.setenv("DECROCHAGE_RATE_LIMIT_PER_MINUTE", "1")
    app = create_app()
    app.state.bundle = ModelBundle(
        pipeline=DummyPipeline(),
        feature_cols=["taux_rendu_devoirs"],
        threshold=0.5,
        catalogue=pd.DataFrame({"filiere": ["Informatique"]}),
    )
    client = TestClient(app)
    payload = {"records": [PREDICTION_RECORD]}

    assert client.post("/predict", json=payload).status_code == 200
    limited = client.post("/predict", json=payload)

    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert limited.headers["X-Request-ID"]


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
