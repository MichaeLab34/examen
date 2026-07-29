"""Portal account model.

`PortalUser` describes a *staff* account (pedagogical referent, programme lead,
data-protection officer), never a student. It inherits from the shared
declarative `Base` so `decrochage init-db` creates it alongside the medallion
tables.

Data minimisation: the login handle is an information-system username, not an
email address. `display_name` is optional and may stay empty.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..persistence import Base

ROLE_REFERENT = "referent"
ROLE_PILOTE = "pilote"
ROLE_AUDITEUR = "auditeur"
ROLES: tuple[str, ...] = (ROLE_REFERENT, ROLE_PILOTE, ROLE_AUDITEUR)

# Scope sentinel returned when `scope_filieres` holds something we cannot read.
# An empty list means "no programme at all", which makes the SQL join match
# nothing. That is deliberate: a corrupted scope must never widen access.
UNREADABLE_SCOPE: list[str] = []


class PortalUser(Base):
    __tablename__ = "portal_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_filieres: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Incremented on logout, password rotation and revocation. The session token
    # carries the epoch it was issued with, so bumping it invalidates every
    # cookie already in circulation without a server-side session table.
    session_epoch: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def scope_list(self) -> list[str] | None:
        """Return the allowed programme names, or None for an unrestricted scope.

        Fail-closed: a stored scope we cannot parse (hand-edited row, migration
        accident) yields an **empty** list, not None. None would mean "every
        programme" and would silently widen a referent's access.
        """
        if self.scope_filieres is None or str(self.scope_filieres).strip() == "":
            return None
        try:
            parsed = json.loads(self.scope_filieres)
        except json.JSONDecodeError:
            return UNREADABLE_SCOPE
        if not isinstance(parsed, list):
            return UNREADABLE_SCOPE
        values = [str(item).strip() for item in parsed if str(item).strip()]
        return values if values else UNREADABLE_SCOPE

    def is_active(self) -> bool:
        """Return True when the account has not been disabled."""
        return self.disabled_at is None


def normalize_scope(filieres: list[str] | None) -> str | None:
    """Serialize a programme scope for storage, normalising case like the pipeline."""
    if not filieres:
        return None
    values = sorted({str(item).strip().title() for item in filieres if str(item).strip()})
    if not values:
        return None
    return json.dumps(values, ensure_ascii=False)
