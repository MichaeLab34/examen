"""FastAPI inference service for the dropout-risk model."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status

from .schemas import HealthResponse, PredictionRequest, PredictionResponse, ReadyResponse
from .serving import ModelBundle, load_bundle, predict_proba_abandon

DEFAULT_MODEL_PATH = Path("artifacts/models/model_bundle.joblib")


def _configured_model_path() -> Path:
    return Path(os.getenv("DECROCHAGE_MODEL_PATH", str(DEFAULT_MODEL_PATH)))


def _configured_api_key() -> str | None:
    return os.getenv("DECROCHAGE_API_KEY") or None


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require `X-API-Key` only when `DECROCHAGE_API_KEY` is configured."""
    expected = _configured_api_key()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def load_configured_bundle() -> tuple[ModelBundle | None, str | None]:
    path = _configured_model_path()
    if not path.exists():
        return None, f"Model file not found: {path}"
    try:
        return load_bundle(path), None
    except Exception as exc:  # pragma: no cover - defensive startup guard
        return None, f"Model load failed: {exc}"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Decrochage Student Dropout Risk API",
        version="0.1.0",
        description="Inference API for early dropout-risk scoring.",
    )

    bundle, load_error = load_configured_bundle()
    app.state.bundle = bundle
    app.state.load_error = load_error
    app.state.model_path = str(_configured_model_path())

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/ready", response_model=ReadyResponse)
    def ready(request: Request) -> ReadyResponse:
        bundle_ready = request.app.state.bundle is not None
        if not bundle_ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=request.app.state.load_error or "Model is not loaded",
            )
        return ReadyResponse(ready=True, model_path=request.app.state.model_path)

    @app.post(
        "/predict",
        response_model=PredictionResponse,
        dependencies=[Depends(require_api_key)],
    )
    def predict(payload: PredictionRequest, request: Request) -> PredictionResponse:
        bundle = request.app.state.bundle
        if bundle is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=request.app.state.load_error or "Model is not loaded",
            )
        raw_df = pd.DataFrame(payload.records)
        scored = predict_proba_abandon(bundle, raw_df)
        return PredictionResponse(predictions=scored.to_dict(orient="records"))

    return app


app = create_app()
