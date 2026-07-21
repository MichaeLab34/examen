"""Operational alert decisions and dead-man's-switch heartbeat support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import json
from typing import Any, Mapping
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class AlertEventSnapshot:
    """Minimal persisted state needed to suppress repeated alerts."""

    triggered_at: datetime
    resolved_at: datetime | None = None


@dataclass(frozen=True)
class AlertDecision:
    """Decision for one drift report."""

    should_alert: bool
    should_resolve: bool
    status: str
    affected_features: tuple[str, ...]
    max_psi: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_drift_alert(
    report: Mapping[str, Any],
    *,
    now: datetime,
    last_event: AlertEventSnapshot | None,
    cooldown: timedelta = timedelta(hours=24),
) -> AlertDecision:
    """Apply hysteresis and a cooldown to a batch PSI report."""

    features = list(report.get("features", []))
    status = str(report.get("summary", {}).get("status", "missing"))
    affected = tuple(str(item.get("feature")) for item in features if item.get("status") == "alert")
    psi_values = [float(item["psi"]) for item in features if item.get("psi") is not None]
    max_psi = max(psi_values, default=0.0)

    if status == "ok":
        active = last_event is not None and last_event.resolved_at is None
        return AlertDecision(False, active, status, (), max_psi)

    if status != "alert":
        return AlertDecision(False, False, status, (), max_psi)

    if last_event is None or last_event.resolved_at is not None:
        return AlertDecision(True, False, status, affected, max_psi)

    should_repeat = now - last_event.triggered_at >= cooldown
    return AlertDecision(should_repeat, False, status, affected, max_psi)


def ping_dead_mans_switch(url: str, *, success: bool = True, timeout_seconds: float = 5.0) -> int:
    """Ping a healthchecks.io-compatible endpoint after a scheduled job."""

    target = url.rstrip("/") if success else f"{url.rstrip('/')}/fail"
    request = Request(target, method="GET", headers={"User-Agent": "decrochage-run/1.0"})
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - operator URL
        return int(response.status)


def post_alert_webhook(
    url: str,
    payload: Mapping[str, Any],
    *,
    timeout_seconds: float = 5.0,
) -> int:
    """Post an operational event to the configured team webhook."""

    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "decrochage-run/1.0",
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - operator URL
        return int(response.status)
