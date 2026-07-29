"""Authentication, session and authorization primitives for the portal.

Design notes:

- Passwords are hashed with Argon2id. No default account is shipped and no
  password is ever accepted on a command line.
- The session cookie carries the username only. Role and programme scope are
  re-read from the database on every request, so disabling an account revokes
  access immediately without a server-side session table.
- Failed logins are throttled per username with a sliding window, and the
  login form returns the same message for unknown users and wrong passwords
  to avoid account enumeration.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from .models import PortalUser

SESSION_COOKIE = "decrochage_portal_session"
SESSION_SALT = "decrochage-portal-session"
CSRF_SALT = "decrochage-portal-csrf"
CSRF_FIELD = "csrf_token"
CSRF_MAX_AGE = 12 * 3600
MAX_TRACKED_LOGIN_KEYS = 4096

_HASHER = PasswordHasher()

# Verified against this constant when the account does not exist, so a wrong
# password and an unknown username cost the same wall-clock time. Without it,
# the ~1 ms / ~90 ms gap enumerates every valid staff username despite the
# identical HTTP response.
_TIMING_EQUALIZER_HASH = _HASHER.hash("timing-equalizer-not-a-credential")


def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    if not password:
        raise ValueError("Password must not be empty")
    return _HASHER.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a password against its Argon2id hash without raising."""
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _serializer(secret: str, salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=salt)


def issue_session(username: str, secret: str, *, epoch: int = 1) -> str:
    """Return a signed session token for `username`, stamped with `epoch`."""
    return _serializer(secret, SESSION_SALT).dumps({"u": username, "e": int(epoch)})


def read_session(token: str | None, secret: str, *, max_age: int) -> tuple[str, int] | None:
    """Return `(username, epoch)` carried by a valid session token, else None.

    The epoch lets the caller reject a token issued before a logout, a password
    rotation or a revocation — a signature check alone cannot do that.
    """
    if not token:
        return None
    try:
        payload = _serializer(secret, SESSION_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(payload, dict):
        return None
    username = payload.get("u")
    if not username:
        return None
    try:
        epoch = int(payload.get("e", 0))
    except (TypeError, ValueError):
        return None
    return str(username), epoch


def issue_csrf(username: str, secret: str) -> str:
    """Return a CSRF token bound to the authenticated username."""
    return _serializer(secret, CSRF_SALT).dumps({"u": username})


def verify_csrf(token: str | None, username: str, secret: str) -> bool:
    """Return True when `token` is a valid CSRF token for `username`."""
    if not token:
        return False
    try:
        payload = _serializer(secret, CSRF_SALT).loads(token, max_age=CSRF_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(payload, dict) and payload.get("u") == username


@dataclass(frozen=True)
class PortalIdentity:
    """Authenticated staff member, resolved from the database on each request."""

    username: str
    role: str
    scope: list[str] | None
    display_name: str | None = None

    @property
    def label(self) -> str:
        """Human-facing label for the header."""
        return self.display_name or self.username

    @property
    def scope_label(self) -> str:
        """Readable programme scope."""
        return ", ".join(self.scope) if self.scope else "toutes filières"

    def has_role(self, *roles: str) -> bool:
        return self.role in roles


class LoginThrottle:
    """Sliding-window limiter for failed login attempts, keyed by username.

    In-memory and per-process, therefore: the budget is multiplied by the number
    of workers, and a restart clears it. Documented as a limitation in
    `docs/threat_model.md`; a shared store is required before scaling out.

    Keys are bounded and expired entries are dropped, so an attacker cycling
    through invented usernames cannot grow the map indefinitely.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = max(1, limit)
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _prune_locked(self, key: str, now: float) -> deque[float]:
        events = self._failures.get(key)
        if events is None:
            return deque()
        cutoff = now - self.window_seconds
        while events and events[0] <= cutoff:
            events.popleft()
        if not events:
            self._failures.pop(key, None)
        return events

    def _evict_locked(self, now: float) -> None:
        if len(self._failures) <= MAX_TRACKED_LOGIN_KEYS:
            return
        cutoff = now - self.window_seconds
        stale = [
            key for key, events in self._failures.items() if not events or events[-1] <= cutoff
        ]
        for key in stale:
            self._failures.pop(key, None)
        while len(self._failures) > MAX_TRACKED_LOGIN_KEYS:
            oldest = min(self._failures, key=lambda item: self._failures[item][-1])
            self._failures.pop(oldest, None)

    def is_locked(self, key: str, *, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        with self._lock:
            return len(self._prune_locked(key, current)) >= self.limit

    def register_failure(self, key: str, *, now: float | None = None) -> int:
        """Record a failed attempt and return the number of attempts in the window."""
        current = monotonic() if now is None else now
        with self._lock:
            events = self._prune_locked(key, current)
            events.append(current)
            self._failures[key] = events
            self._evict_locked(current)
            return len(events)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def tracked_keys(self) -> int:
        """Number of usernames currently tracked (used by tests)."""
        with self._lock:
            return len(self._failures)


def load_user(session: Session, username: str) -> PortalUser | None:
    """Return the account for `username`, or None."""
    return session.query(PortalUser).filter(PortalUser.username == username).one_or_none()


def identity_for(user: PortalUser) -> PortalIdentity:
    """Build a request-scoped identity from a database row."""
    return PortalIdentity(
        username=user.username,
        role=user.role,
        scope=user.scope_list(),
        display_name=user.display_name,
    )


def authenticate(session: Session, username: str, password: str) -> PortalIdentity | None:
    """Return the identity when credentials match an active account, else None.

    The Argon2 verification is always performed — against a constant hash when
    the account is unknown — so response time does not distinguish an unknown
    username from a wrong password. Without this, the identical error message
    would still leak the list of valid staff usernames.
    """
    user = load_user(session, username)
    reference_hash = user.password_hash if user is not None else _TIMING_EQUALIZER_HASH
    password_matches = verify_password(reference_hash, password)

    if user is None or not user.is_active() or not password_matches:
        return None
    return identity_for(user)
