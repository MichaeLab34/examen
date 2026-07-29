"""Restitution portal for pedagogical referents (C7 "Restitution & pilotage").

The portal is the human-facing end of the pipeline: it turns persisted risk
scores into a prioritized, explainable and auditable work list. It is read-only,
handles pseudonyms exclusively, and is disabled unless
`DECROCHAGE_PORTAL_ENABLED` is explicitly turned on.
"""

from __future__ import annotations

from .config import PortalSettings, portal_enabled
from .models import ROLES, PortalUser, normalize_scope
from .routes import BASE_PATH, STATIC_DIR, build_portal_router

__all__ = [
    "BASE_PATH",
    "PortalSettings",
    "PortalUser",
    "ROLES",
    "STATIC_DIR",
    "build_portal_router",
    "normalize_scope",
    "portal_enabled",
]
