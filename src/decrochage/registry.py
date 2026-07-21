"""MLflow Model Registry aliases for candidate, production and rollback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from .operations import PromotionDecision, evaluate_candidate_promotion
from .serving import ModelBundle, load_bundle

ALIASES: tuple[str, ...] = ("candidate", "production", "archived")
METRIC_KEYS: tuple[str, ...] = ("auc_test", "recall_test", "fairness_recall_gap_test")


def _mlflow_modules() -> tuple[Any, Any]:
    import mlflow
    from mlflow import MlflowClient

    return mlflow, MlflowClient


def configure_registry_uri(uri: str | None) -> None:
    """Use one URI for tracking and registry when explicitly configured."""

    if not uri:
        return
    mlflow, _ = _mlflow_modules()
    mlflow.set_tracking_uri(uri)
    mlflow.set_registry_uri(uri)


def _client(uri: str | None = None) -> Any:
    configure_registry_uri(uri)
    _, client_class = _mlflow_modules()
    return client_class()


def _ensure_registered(name: str, *, uri: str | None = None) -> None:
    client = _client(uri)
    try:
        client.get_registered_model(name)
    except Exception:  # Model name does not exist yet.
        client.create_registered_model(name)


def _set_alias(name: str, version: int, alias: str, *, uri: str | None = None) -> None:
    if alias not in ALIASES:
        raise ValueError(f"Invalid alias {alias!r}; expected one of {ALIASES}")
    client = _client(uri)
    client.set_registered_model_alias(name, alias, str(version))
    client.set_model_version_tag(name, str(version), "lifecycle", alias)


def register_bundle(
    bundle_path: str | Path,
    name: str,
    *,
    metrics: Mapping[str, Any] | None = None,
    uri: str | None = None,
) -> int:
    """Register a serialized bundle as a candidate and persist gate metrics."""

    path = Path(bundle_path).resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    _ensure_registered(name, uri=uri)
    client = _client(uri)
    try:
        source = path.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        source = path.as_uri()
    model_version = client.create_model_version(name=name, source=source)
    version = int(model_version.version)
    for key, value in (metrics or {}).items():
        if key in METRIC_KEYS:
            client.set_model_version_tag(name, str(version), f"metric.{key}", str(value))
    _set_alias(name, version, "candidate", uri=uri)
    return version


def register_saved_bundle(bundle_path: str | Path, name: str, *, uri: str | None = None) -> int:
    """Load a saved bundle and register it with the metrics carried in metadata."""

    bundle = load_bundle(bundle_path)
    return register_bundle(bundle_path, name, metrics=bundle.metadata, uri=uri)


def version_at(name: str, alias: str, *, uri: str | None = None) -> Any | None:
    """Return the version referenced by an alias, or ``None`` when absent."""

    try:
        return _client(uri).get_model_version_by_alias(name, alias)
    except Exception:
        return None


def _metrics_for_version(version: Any | None) -> dict[str, float]:
    if version is None:
        return {}
    metrics: dict[str, float] = {}
    for key in METRIC_KEYS:
        value = version.tags.get(f"metric.{key}")
        if value is not None:
            metrics[key] = float(value)
    return metrics


def promote_candidate(
    name: str,
    version: int,
    *,
    human_approved: bool,
    uri: str | None = None,
) -> PromotionDecision:
    """Run the technical gate, then move the production alias after approval."""

    client = _client(uri)
    candidate = client.get_model_version(name, str(version))
    production = version_at(name, "production", uri=uri)
    decision = evaluate_candidate_promotion(
        _metrics_for_version(candidate),
        production_metrics=_metrics_for_version(production) or None,
        human_approved=human_approved,
    )
    if not decision.approved_for_production:
        return decision

    if production is not None and int(production.version) != version:
        _set_alias(name, int(production.version), "archived", uri=uri)
    _set_alias(name, version, "production", uri=uri)
    return decision


def rollback_production(name: str, to_version: int, *, uri: str | None = None) -> None:
    """Point production back to a previous version and archive the replaced one."""

    current = version_at(name, "production", uri=uri)
    if current is not None and int(current.version) != to_version:
        _set_alias(name, int(current.version), "archived", uri=uri)
    _set_alias(name, to_version, "production", uri=uri)


def _file_uri_to_path(source: str) -> Path:
    parsed = urlparse(source)
    if parsed.scheme not in {"", "file"}:
        raise ValueError(f"Unsupported bundle source URI: {source}")
    raw_path = unquote(parsed.path if parsed.scheme else source)
    if len(raw_path) >= 3 and raw_path[0] == "/" and raw_path[2] == ":":
        raw_path = raw_path[1:]
    return Path(raw_path)


def load_bundle_by_alias(
    name: str, alias: str = "production", *, uri: str | None = None
) -> tuple[ModelBundle, str]:
    """Resolve an alias and load the corresponding joblib bundle."""

    version = version_at(name, alias, uri=uri)
    if version is None:
        raise FileNotFoundError(f"No {alias!r} alias for registered model {name!r}")
    bundle = load_bundle(_file_uri_to_path(version.source))
    return bundle, str(version.version)
