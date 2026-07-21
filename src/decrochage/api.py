"""FastAPI inference service for the dropout-risk model."""

from __future__ import annotations

from collections import defaultdict, deque
import json
import logging
import os
from pathlib import Path
import re
from threading import Lock
from time import monotonic, perf_counter
from uuid import uuid4

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse

from .registry import load_bundle_by_alias
from .schemas import (
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
    ReadyResponse,
    ReloadResponse,
)
from .serving import ModelBundle, load_bundle, predict_proba_abandon

DEFAULT_MODEL_PATH = Path("artifacts/models/model_bundle.joblib")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
AUDIT_LOGGER = logging.getLogger("decrochage.api.audit")
AUDIT_LOGGER.setLevel(logging.INFO)


class SlidingWindowRateLimiter:
    """Thread-safe limiter for the single-instance prototype API."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = max(0, limit)
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        if self.limit == 0:
            return True, 0
        current = monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            events = self._requests[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (current - events[0])) + 1)
                return False, retry_after
            events.append(current)
            return True, 0


def _configured_model_path() -> Path:
    return Path(os.getenv("DECROCHAGE_MODEL_PATH", str(DEFAULT_MODEL_PATH)))


def _configured_api_key() -> str | None:
    return os.getenv("DECROCHAGE_API_KEY") or None


def _configured_registered_model() -> str | None:
    return os.getenv("DECROCHAGE_REGISTERED_MODEL") or None


def _configured_model_alias() -> str:
    return os.getenv("DECROCHAGE_MODEL_ALIAS", "production")


def _configured_registry_uri() -> str | None:
    return os.getenv("MLFLOW_TRACKING_URI") or None


def _configured_rate_limit() -> int:
    value = os.getenv("DECROCHAGE_RATE_LIMIT_PER_MINUTE", "60")
    try:
        return max(0, int(value))
    except ValueError as exc:
        raise ValueError("DECROCHAGE_RATE_LIMIT_PER_MINUTE must be an integer") from exc


def _request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require `X-API-Key` only when `DECROCHAGE_API_KEY` is configured."""
    expected = _configured_api_key()
    if expected and x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Protect model reload even when public prediction authentication is disabled."""

    expected = _configured_api_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DECROCHAGE_API_KEY must be configured for administrative actions",
        )
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def load_configured_bundle() -> tuple[ModelBundle | None, str | None, str | None, str]:
    registered_model = _configured_registered_model()
    if registered_model:
        alias = _configured_model_alias()
        try:
            bundle, version = load_bundle_by_alias(
                registered_model,
                alias,
                uri=_configured_registry_uri(),
            )
            return bundle, None, version, f"models:/{registered_model}@{alias}"
        except Exception as exc:  # pragma: no cover - defensive startup guard
            return None, f"Registry model load failed: {exc}", None, registered_model

    path = _configured_model_path()
    if not path.exists():
        return None, f"Model file not found: {path}", None, str(path)
    try:
        return load_bundle(path), None, None, str(path)
    except Exception as exc:  # pragma: no cover - defensive startup guard
        return None, f"Model load failed: {exc}", None, str(path)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Decrochage Student Dropout Risk API",
        version="0.1.0",
        description="Inference API for early dropout-risk scoring.",
    )

    bundle, load_error, model_version, model_source = load_configured_bundle()
    app.state.bundle = bundle
    app.state.load_error = load_error
    app.state.model_path = model_source
    app.state.model_version = model_version
    app.state.model_alias = _configured_model_alias() if _configured_registered_model() else None
    app.state.rate_limiter = SlidingWindowRateLimiter(_configured_rate_limit())

    @app.middleware("http")
    async def operational_controls(request: Request, call_next):
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        started = perf_counter()
        client_host = request.client.host if request.client else "unknown"
        response = None
        try:
            if request.url.path in {"/predict", "/admin/reload"}:
                allowed, retry_after = request.app.state.rate_limiter.allow(
                    f"{client_host}:{request.url.path}"
                )
                if not allowed:
                    response = JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Rate limit exceeded"},
                        headers={"Retry-After": str(retry_after)},
                    )
                else:
                    response = await call_next(request)
            else:
                response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            AUDIT_LOGGER.info(
                json.dumps(
                    {
                        "event": "api_request",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status": response.status_code if response is not None else 500,
                        "duration_ms": round((perf_counter() - started) * 1000, 2),
                    },
                    separators=(",", ":"),
                )
            )

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
        return ReadyResponse(
            ready=True,
            model_path=request.app.state.model_path,
            model_version=request.app.state.model_version,
            model_alias=request.app.state.model_alias,
        )

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

    @app.post(
        "/admin/reload",
        response_model=ReloadResponse,
        dependencies=[Depends(require_admin_api_key)],
    )
    def reload_model(request: Request) -> ReloadResponse:
        bundle, load_error, version, source = load_configured_bundle()
        if bundle is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=load_error or "Model reload failed",
            )
        request.app.state.bundle = bundle
        request.app.state.load_error = None
        request.app.state.model_path = source
        request.app.state.model_version = version
        request.app.state.model_alias = (
            _configured_model_alias() if _configured_registered_model() else None
        )
        return ReloadResponse(
            reloaded=True,
            model_path=source,
            model_version=version,
            model_alias=request.app.state.model_alias,
        )

    Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,
    )

    return app


app = create_app()
