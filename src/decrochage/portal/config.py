"""Portal configuration resolved from the environment at call time.

The pattern mirrors `decrochage.api._configured_*`: every value is read from
`os.environ` when requested, so tests can use `monkeypatch.setenv` without
reloading the module.
"""

from __future__ import annotations

from dataclasses import dataclass
import os

ENABLED_ENV = "DECROCHAGE_PORTAL_ENABLED"
SECRET_ENV = "DECROCHAGE_PORTAL_SECRET"
SESSION_HOURS_ENV = "DECROCHAGE_PORTAL_SESSION_HOURS"
PAGE_SIZE_ENV = "DECROCHAGE_PORTAL_PAGE_SIZE"
EXPORT_MAX_ROWS_ENV = "DECROCHAGE_PORTAL_EXPORT_MAX_ROWS"
LOGIN_ATTEMPTS_ENV = "DECROCHAGE_PORTAL_LOGIN_MAX_ATTEMPTS"
LOGIN_WINDOW_ENV = "DECROCHAGE_PORTAL_LOGIN_WINDOW_MINUTES"
COOKIE_INSECURE_ENV = "DECROCHAGE_PORTAL_ALLOW_INSECURE_COOKIE"

_TRUE_VALUES = {"1", "true", "yes", "on"}
MAX_PAGE = 10_000


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    return max(minimum, value)


def portal_enabled() -> bool:
    """Return True when the operator explicitly opted the portal in."""
    return (os.getenv(ENABLED_ENV, "false") or "").strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class PortalSettings:
    """Immutable snapshot of the portal configuration."""

    enabled: bool
    secret: str
    session_hours: int = 8
    page_size: int = 50
    export_max_rows: int = 1000
    login_max_attempts: int = 5
    login_window_minutes: int = 15
    cookie_secure: bool = True

    @property
    def session_max_age(self) -> int:
        """Session lifetime in seconds."""
        return self.session_hours * 3600

    @property
    def login_window_seconds(self) -> float:
        """Throttling window in seconds."""
        return float(self.login_window_minutes * 60)

    @classmethod
    def from_env(cls) -> PortalSettings:
        """Build settings from the environment.

        When the portal is disabled, no other variable is read: a typo in a
        portal setting must never prevent a pure inference deployment from
        starting.

        Raises:
            ValueError: when the portal is enabled without a session secret.
                Failing at startup is deliberate: an unsigned session cookie
                would be forgeable.
        """
        if not portal_enabled():
            return cls(enabled=False, secret="")

        secret = os.getenv(SECRET_ENV, "") or ""
        if not secret.strip():
            raise ValueError(f"{SECRET_ENV} is required when {ENABLED_ENV} is enabled")
        # Secure by default and opt-out explicitly: deriving it from the request
        # scheme silently fails behind a reverse proxy, because uvicorn only
        # trusts `X-Forwarded-Proto` from `forwarded_allow_ips` (127.0.0.1 by
        # default), which excludes a Caddy container on the compose network.
        allow_insecure = (os.getenv(COOKIE_INSECURE_ENV, "") or "").strip().lower()
        return cls(
            enabled=True,
            secret=secret,
            session_hours=_env_int(SESSION_HOURS_ENV, 8),
            page_size=_env_int(PAGE_SIZE_ENV, 50),
            export_max_rows=_env_int(EXPORT_MAX_ROWS_ENV, 1000),
            login_max_attempts=_env_int(LOGIN_ATTEMPTS_ENV, 5),
            login_window_minutes=_env_int(LOGIN_WINDOW_ENV, 15),
            cookie_secure=allow_insecure not in _TRUE_VALUES,
        )
