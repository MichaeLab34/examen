"""FastAPI inference service for the dropout-risk model."""

from __future__ import annotations

from collections import defaultdict, deque
import json
import os
from pathlib import Path
import re
from threading import Lock
from time import monotonic, perf_counter
from uuid import uuid4

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.responses import JSONResponse

from .logging_config import configure_json_logger
from .portal.config import PortalSettings
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
AUDIT_LOGGER = configure_json_logger("decrochage.api.audit")

# Paths protected by the application rate limiter. `/portal/login` is included
# so the portal login form is throttled at the edge of the service as well as by
# the per-account lockout, which blunts credential stuffing across usernames.
RATE_LIMITED_PATHS = frozenset({"/predict", "/admin/reload", "/portal/login"})


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
            if request.url.path in RATE_LIMITED_PATHS:
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

    _mount_portal(app)

    return app


def _mount_portal(app: FastAPI) -> None:
    """Mount the restitution portal when the operator opted in.

    Kept out of the default path on purpose: a pure inference deployment
    (SI/LMS integration) then exposes no authenticated web surface at all. The
    import is local so the API keeps working even if the portal package is
    removed from a trimmed image.
    """
    settings = PortalSettings.from_env()
    if not settings.enabled:
        app.state.portal_enabled = False
        return

    from .portal import STATIC_DIR, build_portal_router

    app.include_router(build_portal_router(settings))
    app.mount(
        "/portal/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="portal-static",
    )
    app.state.portal_enabled = True


app = create_app()
