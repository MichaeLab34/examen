"""HTTP routes of the restitution portal.

Everything is server-rendered and read-only. The portal never triggers a scoring
run: it reads what the batch pipeline persisted, so every figure it shows is
attached to an auditable ingestion batch and falls under the retention policy.

Security posture:

- Unauthenticated access redirects to the login form (303) and never leaks content.
- A role that may not use a route gets 403; a record outside the user's programme
  scope gets 404, so a scope boundary never confirms that a record exists.
- Every sensitive view and every export writes a `PrivacyAuditLog` row with the
  staff username as actor and a pseudonym as target.
- Query parameters are parsed permissively (an emptied form field falls back to
  its default) but bounded, so a user never faces a raw 422 and a hostile value
  never reaches SQL, an HTTP header or a CSV cell.

Access control uses an explicit early return (`guard` returns either an identity
or a ready-made response) rather than exceptions, so the portal never installs
exception handlers on the shared FastAPI application.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlencode

import pandas as pd
from fastapi import APIRouter, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .. import features as F
from ..persistence import make_session_factory, record_privacy_audit
from ..serving import ModelBundle, can_explain, explain_prediction, prepare_features
from . import repository as repo
from .config import MAX_PAGE, PortalSettings
from .labels import format_value, humanize_feature, is_displayable_factor
from .models import ROLE_AUDITEUR, ROLE_PILOTE, ROLE_REFERENT
from .security import (
    SESSION_COOKIE,
    LoginThrottle,
    PortalIdentity,
    authenticate,
    identity_for,
    issue_csrf,
    issue_session,
    load_user,
    read_session,
    verify_csrf,
)

BASE_PATH = "/portal"
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

USERNAME_PATTERN = r"^[A-Za-z0-9._-]{1,80}$"
BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
FILENAME_UNSAFE = re.compile(r"[^A-Za-z0-9_-]")
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

# Responses carry a student risk assessment: no intermediary, browser cache or
# back-button restore may retain them.
NO_STORE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    "Pragma": "no-cache",
}

# Set by the application itself, not only by the Caddyfile: the portal must not
# depend on a reverse proxy being in front of it for its main anti-XSS control.
# A local run, a different ingress or a misordered route would otherwise serve
# HTML with no policy at all. Caddy sets the same values, and a `header` block
# replaces rather than appends, so nothing is duplicated downstream.
HTML_SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; "
        "script-src 'self'; form-action 'self'; frame-ancestors 'none'; "
        "base-uri 'none'; object-src 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-Robots-Tag": "noindex, nofollow",
}

ROLE_LABELS = {
    ROLE_REFERENT: "référent pédagogique",
    ROLE_PILOTE: "pilotage réussite étudiante",
    ROLE_AUDITEUR: "délégué à la protection des données",
}

CONSULTATION_MOTIFS: list[tuple[str, str]] = [
    ("preparation_entretien", "Préparation d'un entretien"),
    ("revue_commission", "Revue en commission de suivi"),
    ("suivi_dispositif", "Suivi d'un dispositif déjà engagé"),
]
DEFAULT_MOTIF = CONSULTATION_MOTIFS[0][0]
MOTIF_LABELS = dict(CONSULTATION_MOTIFS)

HISTOGRAM_WIDTH = 640
HISTOGRAM_HEIGHT = 220
HISTOGRAM_PADDING_BOTTOM = 18

EXPORT_COLUMNS = [
    "pseudo_id",
    "rang",
    "proba_abandon",
    "alerte",
    "filiere",
    "batch_id",
    "model_version",
    "threshold",
    "generated_at",
]

METRIC_LABELS: list[tuple[str, str]] = [
    ("auc_test", "AUC (jeu de test)"),
    ("average_precision_test", "Précision moyenne (test)"),
    ("recall_test", "Rappel (test)"),
    ("precision_test", "Précision (test)"),
    ("f1_test", "F1 (test)"),
    ("fairness_recall_gap_test", "Écart de rappel entre sous-groupes"),
    ("n_train", "Effectif d'entraînement"),
    ("n_validation", "Effectif de validation"),
    ("n_test", "Effectif de test"),
    ("n_features", "Nombre de variables"),
]

_FALSE_FLAGS = {"", "0", "false", "no", "off", "non"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _flag(raw: str | None) -> bool:
    """Interpret a checkbox-style parameter, treating `0`/`false` as unchecked."""
    return raw is not None and str(raw).strip().lower() not in _FALSE_FLAGS


def _int_param(raw: str | None, default: int, *, minimum: int, maximum: int) -> int:
    """Parse an integer query parameter permissively, then bound it.

    An emptied form field must not produce a raw 422 JSON page in a portal used
    by non-technical staff; it falls back to the default instead.
    """
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(str(raw).strip())
    except ValueError:
        return default
    return min(maximum, max(minimum, value))


def _float_param(raw: str | None, *, minimum: float, maximum: float) -> float | None:
    if raw is None or str(raw).strip() == "":
        return None
    try:
        value = float(str(raw).strip().replace(",", "."))
    except ValueError:
        return None
    if value != value:  # NaN
        return None
    return min(maximum, max(minimum, value))


def _safe_next(raw: str | None) -> str:
    """Return a safe internal redirect target, guarding against open redirects."""
    if not raw:
        return f"{BASE_PATH}/"
    if raw.startswith(f"{BASE_PATH}/") and "//" not in raw and "\\" not in raw:
        return raw
    return f"{BASE_PATH}/"


def _threshold_label(value: float | None) -> str:
    return f"{value:.2f}" if value is not None else "non renseigné"


def _csv_safe(value: Any) -> str:
    """Neutralize spreadsheet formula injection in an exported cell.

    The export is opened by the registrar's office; a `filiere` coming from the
    source CSV as `=cmd|...` would otherwise become an active cell.
    """
    text = "" if value is None else str(value)
    if text[:1] in CSV_FORMULA_PREFIXES:
        return "'" + text
    return text


def _nav_items(identity: PortalIdentity, current_path: str) -> list[dict[str, Any]]:
    items: list[tuple[str, str]] = []
    if identity.has_role(ROLE_REFERENT):
        items.append((f"{BASE_PATH}/cohorte", "Cohorte priorisée"))
    if identity.has_role(ROLE_REFERENT, ROLE_PILOTE):
        items.append((f"{BASE_PATH}/pilotage", "Pilotage"))
    if identity.has_role(ROLE_AUDITEUR):
        items.append((f"{BASE_PATH}/conformite", "Conformité"))
    items.append((f"{BASE_PATH}/a-propos", "À propos du modèle"))
    return [
        {"href": href, "label": label, "current": current_path.startswith(href)}
        for href, label in items
    ]


def _histogram_bars(buckets: list[tuple[float, float, int]]) -> list[dict[str, Any]]:
    """Convert probability buckets into pre-computed SVG rectangles.

    Geometry is computed server-side so the template needs no inline style, which
    is what lets the Content-Security-Policy stay strict.
    """
    if not buckets:
        return []
    highest = max(count for _, _, count in buckets) or 1
    usable_height = HISTOGRAM_HEIGHT - HISTOGRAM_PADDING_BOTTOM
    slot = HISTOGRAM_WIDTH / len(buckets)
    bar_width = slot * 0.8
    bars = []
    for index, (lower, upper, count) in enumerate(buckets):
        height = round(usable_height * count / highest, 1)
        x = round(index * slot + (slot - bar_width) / 2, 1)
        bars.append(
            {
                "x": x,
                "y": round(usable_height - height, 1),
                "width": round(bar_width, 1),
                "height": height,
                "count": count,
                "label": f"{lower:.1f}",
                "label_x": round(x + bar_width / 2, 1),
                "range_label": f"{lower:.1f} – {upper:.1f}",
            }
        )
    return bars


def _excluded_groups() -> list[dict[str, str]]:
    """Describe the locked scoring perimeter for the "about" page."""
    return [
        {
            "title": "Fuite de données",
            "columns": ", ".join(F.LEAKAGE_TARGET_COLS),
            "reason": (
                "Résultat de fin de semestre : structurellement corrélé au décrochage, "
                "il rendrait la performance illusoire."
            ),
        },
        {
            "title": "Fuite temporelle",
            "columns": ", ".join(F.LEAKAGE_TEMPORAL_COLS),
            "reason": (
                "Consolidées en fin de semestre 1, donc indisponibles au moment du "
                "scoring à mi-semestre."
            ),
        },
        {
            "title": "Identifiants directs",
            "columns": ", ".join(F.ID_COLS),
            "reason": "Aucun pouvoir prédictif et risque de sur-apprentissage.",
        },
        {
            "title": "Leurres",
            "columns": ", ".join(F.LEURRE_COLS),
            "reason": "Variables sans lien causal ni prédictif, analysées puis écartées.",
        },
        {
            "title": "Texte libre",
            "columns": F.TEXT_COL,
            "reason": (
                "Seule la présence d'un commentaire est conservée ; le contenu n'est pas "
                "exploité."
            ),
        },
    ]


def _build_explanation(
    bundle: ModelBundle | None, stored_payload: dict[str, Any]
) -> tuple[dict[str, Any] | None, str]:
    """Return the display-ready explanation, or an explicit reason why there is none.

    Only `raw_value` is ever shown. The transformed value is what the model
    multiplied by its coefficient, but displaying it would print a standardized
    -1.8 as "-180 %" next to the real figure in "Variables observées".
    """
    if bundle is None:
        return None, "aucun modèle n'est chargé par le service."
    if not can_explain(bundle):
        return None, "le modèle chargé n'est pas un modèle linéaire décomposable."
    stored_input = stored_payload.get("input")
    if not isinstance(stored_input, dict) or not stored_input:
        return None, "les variables d'entrée de cette prédiction n'ont pas été conservées."

    try:
        raw_df = pd.DataFrame([stored_input])
        gold_features = prepare_features(raw_df, bundle.feature_cols, bundle.catalogue)
        explanation = explain_prediction(bundle, gold_features)
    except Exception:  # pragma: no cover - defensive: never break a risk sheet
        return None, "les variables conservées ne permettent pas de rejouer le calcul."

    def as_rows(items: Any) -> list[dict[str, str]]:
        return [
            {
                "label": humanize_feature(item.name),
                "value": format_value(item.source_column or item.name, item.raw_value),
            }
            for item in items
            if is_displayable_factor(item.source_column)
        ]

    # A larger pool is requested because protected attributes and batch-relative
    # variables are filtered out afterwards.
    return {
        "risk": as_rows(explanation.risk_factors(12))[:5],
        "protective": as_rows(explanation.protective_factors(12))[:5],
    }, ""


def build_portal_router(settings: PortalSettings) -> APIRouter:
    """Build the portal router for the given settings."""
    router = APIRouter(prefix=BASE_PATH, tags=["portal"])
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    throttle = LoginThrottle(settings.login_max_attempts, settings.login_window_seconds)

    def open_session() -> Session:
        return make_session_factory()()

    def resolve_identity(request: Request) -> PortalIdentity | None:
        """Re-read the account on every request so revocation is immediate."""
        parsed = read_session(
            request.cookies.get(SESSION_COOKIE),
            settings.secret,
            max_age=settings.session_max_age,
        )
        if parsed is None:
            return None
        username, epoch = parsed
        with open_session() as session:
            user = load_user(session, username)
            if user is None or not user.is_active():
                return None
            # A token issued before a logout, a password rotation or a revocation
            # carries an outdated epoch and must be refused.
            if int(user.session_epoch) != epoch:
                return None
            return identity_for(user)

    def bump_session_epoch(username: str) -> None:
        with open_session() as session:
            user = load_user(session, username)
            if user is not None:
                user.session_epoch = int(user.session_epoch) + 1
                session.commit()

    def render(
        request: Request,
        name: str,
        identity: PortalIdentity | None,
        context: dict[str, Any],
        *,
        status_code: int = status.HTTP_200_OK,
    ) -> HTMLResponse:
        payload: dict[str, Any] = {
            "base_path": BASE_PATH,
            "identity": identity,
            "role_label": ROLE_LABELS.get(identity.role, identity.role) if identity else "",
            "csrf_token": issue_csrf(identity.username, settings.secret) if identity else "",
            "nav_items": _nav_items(identity, request.url.path) if identity else [],
            "now": _now(),
            "flash": None,
            "request_path": request.url.path,
        }
        payload.update(context)
        return templates.TemplateResponse(
            request,
            name,
            payload,
            status_code=status_code,
            headers={**NO_STORE_HEADERS, **HTML_SECURITY_HEADERS},
        )

    def error_page(
        request: Request,
        identity: PortalIdentity | None,
        *,
        status_code: int,
        heading: str,
        message: str,
    ) -> HTMLResponse:
        return render(
            request,
            "error.html",
            identity,
            {"status": status_code, "heading": heading, "message": message},
            status_code=status_code,
        )

    def guard(request: Request, *roles: str) -> PortalIdentity | Response:
        """Return the identity, or the response to send back immediately."""
        identity = resolve_identity(request)
        if identity is None:
            target = f"{BASE_PATH}/login?{urlencode({'next': request.url.path})}"
            return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)
        if roles and not identity.has_role(*roles):
            return error_page(
                request,
                identity,
                status_code=status.HTTP_403_FORBIDDEN,
                heading="Accès non autorisé",
                message=(
                    "Votre rôle ne donne pas accès à cette vue. Si vous pensez qu'il "
                    "s'agit d'une erreur, contactez l'administrateur fonctionnel."
                ),
            )
        return identity

    def audit(
        session: Session,
        identity: PortalIdentity,
        *,
        action: str,
        target_type: str,
        target_id: str | None,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        record_privacy_audit(
            session,
            action=action,
            actor=identity.username[:120],
            target_type=target_type,
            target_id=(target_id[:120] if target_id else None),
            reason=reason,
            metadata=metadata or {},
        )
        session.commit()

    def resolve_batch(session: Session, raw: str | None) -> str | None:
        """Validate a batch id against known batches, else fall back to the latest."""
        candidate = (raw or "").strip()
        if (
            candidate
            and BATCH_ID_PATTERN.fullmatch(candidate)
            and repo.batch_exists(session, candidate)
        ):
            return candidate
        return repo.latest_batch_id(session)

    def resolve_filiere(session: Session, raw: str | None, scope: list[str] | None) -> str | None:
        """Keep a programme filter only when it is one the user may actually see."""
        candidate = (raw or "").strip()
        if not candidate:
            return None
        allowed = repo.available_filieres(session, scope)
        normalized = candidate.title()
        return normalized if normalized in allowed else None

    def batch_context(
        batches: list[repo.BatchInfo],
        batch_id: str | None,
        context: repo.ModelContext,
    ) -> dict[str, Any]:
        selected = next((item for item in batches if item.batch_id == batch_id), None)
        return {
            "batch_short": selected.short_id if selected else ((batch_id or "")[:8] or None),
            "batch_date": (
                selected.created_at.strftime("%d/%m/%Y")
                if selected and selected.created_at
                else None
            ),
            "model_version": context.model_version,
            "threshold_label": _threshold_label(context.threshold),
        }

    def current_bundle(request: Request) -> ModelBundle | None:
        return getattr(request.app.state, "bundle", None)

    # --- Authentification --------------------------------------------------

    @router.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, next: str | None = None) -> HTMLResponse:
        return render(request, "login.html", None, {"next_url": _safe_next(next)})

    @router.post("/login")
    def login_submit(
        request: Request,
        username: str = Form(..., max_length=80, pattern=USERNAME_PATTERN),
        password: str = Form(..., max_length=256),
        next_url: str | None = Form(default=None, alias="next", max_length=512),
    ) -> Response:
        handle = username.strip()
        safe_target = _safe_next(next_url)

        if throttle.is_locked(handle):
            return render(
                request,
                "login.html",
                None,
                {
                    "flash": (
                        "Trop de tentatives infructueuses. Réessayez dans "
                        f"{settings.login_window_minutes} minutes."
                    ),
                    "next_url": safe_target,
                },
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        with open_session() as session:
            identity = authenticate(session, handle, password)
            if identity is None:
                attempts = throttle.register_failure(handle)
                record_privacy_audit(
                    session,
                    action="portal_login_failed",
                    actor=handle[:120] or "inconnu",
                    target_type="portal_user",
                    target_id=None,
                    reason="Tentative de connexion au portail refusée",
                    metadata={"attempts_in_window": attempts},
                )
                session.commit()
                # Same wording for an unknown account and a wrong password.
                return render(
                    request,
                    "login.html",
                    None,
                    {
                        "flash": "Identifiant ou mot de passe incorrect.",
                        "next_url": safe_target,
                    },
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            user = load_user(session, handle)
            epoch = int(user.session_epoch) if user is not None else 1
            must_change = bool(user.must_change_password) if user is not None else False
            if user is not None:
                user.last_login_at = _now()
            record_privacy_audit(
                session,
                action="portal_login",
                actor=identity.username,
                target_type="portal_user",
                target_id=None,
                reason="Connexion au portail de restitution",
                # Traced because an initial password is known to the administrator:
                # any consultation made before rotation is weakly attributable.
                metadata={"role": identity.role, "must_change_password": must_change},
            )
            session.commit()

        throttle.reset(handle)
        response = RedirectResponse(url=safe_target, status_code=status.HTTP_303_SEE_OTHER)
        response.set_cookie(
            SESSION_COOKIE,
            issue_session(identity.username, settings.secret, epoch=epoch),
            max_age=settings.session_max_age,
            httponly=True,
            samesite="strict",
            secure=settings.cookie_secure,
            path=BASE_PATH,
        )
        return response

    @router.post("/logout")
    def logout(request: Request, csrf_token: str = Form(default="", max_length=512)) -> Response:
        identity = resolve_identity(request)
        if identity is None:
            # No side effect for an unauthenticated caller: otherwise a
            # cross-site form could force a logout despite SameSite=Strict.
            return RedirectResponse(url=f"{BASE_PATH}/login", status_code=status.HTTP_303_SEE_OTHER)
        if not verify_csrf(csrf_token, identity.username, settings.secret):
            return error_page(
                request,
                identity,
                status_code=status.HTTP_400_BAD_REQUEST,
                heading="Requête invalide",
                message="Jeton anti-CSRF absent ou expiré. Revenez en arrière et réessayez.",
            )
        # Invalidate every token already issued for this account, not just this cookie.
        bump_session_epoch(identity.username)
        response = RedirectResponse(url=f"{BASE_PATH}/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie(SESSION_COOKIE, path=BASE_PATH)
        return response

    @router.get("/")
    def home(request: Request) -> Response:
        identity = resolve_identity(request)
        if identity is None:
            return RedirectResponse(url=f"{BASE_PATH}/login", status_code=status.HTTP_303_SEE_OTHER)
        target = {
            ROLE_REFERENT: f"{BASE_PATH}/cohorte",
            ROLE_PILOTE: f"{BASE_PATH}/pilotage",
            ROLE_AUDITEUR: f"{BASE_PATH}/conformite",
        }.get(identity.role, f"{BASE_PATH}/a-propos")
        return RedirectResponse(url=target, status_code=status.HTTP_303_SEE_OTHER)

    # --- Cohorte priorisée -------------------------------------------------

    @router.get("/cohorte", response_class=HTMLResponse)
    def cohorte(
        request: Request,
        batch_id: str | None = None,
        filiere: str | None = None,
        alertes: str | None = None,
        capacite: str | None = None,
        page: str | None = None,
    ) -> Response:
        identity = guard(request, ROLE_REFERENT)
        if isinstance(identity, Response):
            return identity
        bundle = current_bundle(request)
        capacity = _int_param(capacite, 0, minimum=0, maximum=settings.export_max_rows)
        page_number = _int_param(page, 1, minimum=1, maximum=MAX_PAGE)

        with open_session() as session:
            batches = repo.list_batches(session)
            selected_batch = resolve_batch(session, batch_id)
            selected_filiere = resolve_filiere(session, filiere, identity.scope)
            filters = repo.CohortFilters(
                batch_id=selected_batch,
                filiere=selected_filiere,
                alerts_only=_flag(alertes),
                page=page_number,
                scope=identity.scope,
            )
            cohort_page = repo.list_predictions(session, filters, page_size=settings.page_size)
            filieres = repo.available_filieres(session, identity.scope)
            context = repo.model_context(session, filters)
            covered = repo.count_alerts_in_top(session, filters, top_k=capacity)
            audit(
                session,
                identity,
                action="portal_view_cohort",
                target_type="ingestion_batch",
                target_id=selected_batch,
                reason="Consultation de la liste priorisée pour accompagnement humain",
                metadata={
                    "rows_served": len(cohort_page.rows),
                    "rows_scanned": max(capacity, len(cohort_page.rows)),
                    "scope": identity.scope if identity.scope is not None else "global",
                    "filiere": selected_filiere,
                    "alerts_only": filters.alerts_only,
                    "page": cohort_page.page,
                },
            )

        query_base: dict[str, Any] = {
            "batch_id": selected_batch or "",
            "filiere": selected_filiere or "",
            "capacite": capacity,
        }
        if filters.alerts_only:
            query_base["alertes"] = "1"

        def page_url(target_page: int) -> str:
            params = dict(query_base)
            params["page"] = target_page
            return f"{BASE_PATH}/cohorte?{urlencode(params)}"

        ratio = (covered / cohort_page.alert_count) if cohort_page.alert_count else 0.0
        return render(
            request,
            "cohorte.html",
            identity,
            {
                "page": cohort_page,
                "filters": filters,
                "batches": batches,
                "filieres": filieres,
                "capacite": capacity,
                "coverage": {"covered": covered, "ratio_label": f"{ratio * 100:.0f} %"},
                "context": batch_context(batches, selected_batch, context),
                "page_url": page_url,
                "export_url": f"{BASE_PATH}/export.csv?{urlencode(query_base)}",
                "export_max_rows": settings.export_max_rows,
                "bundle_loaded": bundle is not None,
            },
        )

    # --- Fiche de risque ---------------------------------------------------

    @router.get("/etudiant/{pseudo_id}", response_class=HTMLResponse)
    def fiche_etudiant(
        request: Request,
        pseudo_id: str,
        batch_id: str | None = None,
        motif: str = DEFAULT_MOTIF,
    ) -> Response:
        identity = guard(request, ROLE_REFERENT)
        if isinstance(identity, Response):
            return identity
        bundle = current_bundle(request)
        selected_motif = motif if motif in MOTIF_LABELS else DEFAULT_MOTIF

        with open_session() as session:
            requested_batch = (batch_id or "").strip()
            scoped_batch = (
                requested_batch
                if requested_batch and BATCH_ID_PATTERN.fullmatch(requested_batch)
                else None
            )
            row = repo.get_prediction(
                session, pseudo_id, scope=identity.scope, batch_id=scoped_batch
            )
            if row is None:
                # 404 rather than 403: a scope boundary must not confirm existence.
                return error_page(
                    request,
                    identity,
                    status_code=status.HTTP_404_NOT_FOUND,
                    heading="Dossier introuvable",
                    message=(
                        "Aucun dossier scoré ne correspond à cet identifiant dans votre "
                        "périmètre."
                    ),
                )

            history = repo.student_history(session, pseudo_id, scope=identity.scope)
            observed_raw = (
                repo.scoring_payload(session, pseudo_id, row.batch_id, bundle.feature_cols)
                if bundle is not None
                else {}
            )
            stored_payload = repo.raw_payload(session, pseudo_id, row.batch_id)
            audit(
                session,
                identity,
                action="portal_view_student",
                target_type="gold_prediction",
                target_id=pseudo_id,
                reason=MOTIF_LABELS[selected_motif],
                metadata={"batch_id": row.batch_id, "motif": selected_motif},
            )

        explanation, explanation_error = _build_explanation(bundle, stored_payload)
        observed = [
            {"label": humanize_feature(name), "value": format_value(name, value)}
            for name, value in sorted(observed_raw.items())
        ]

        trend_label = ""
        if len(history) > 1:
            delta = history[-1].proba_abandon - history[0].proba_abandon
            if delta > 0.05:
                trend_label = "Tendance : aggravation du risque entre le premier et le dernier lot."
            elif delta < -0.05:
                trend_label = (
                    "Tendance : amélioration du risque entre le premier et le dernier lot."
                )
            else:
                trend_label = "Tendance : risque stable entre les lots observés."

        return render(
            request,
            "etudiant.html",
            identity,
            {
                "row": row,
                "history": history,
                "trend_label": trend_label,
                "observed": observed,
                "explanation": explanation,
                "explanation_error": explanation_error,
                "threshold_label": _threshold_label(row.threshold),
                "motifs": CONSULTATION_MOTIFS,
                "motif": selected_motif,
                "back_url": f"{BASE_PATH}/cohorte?{urlencode({'batch_id': row.batch_id})}",
            },
        )

    # --- Export vers le SI -------------------------------------------------
    #
    # Réservé au rôle `referent`. Le rôle `pilote` est refusé sur /cohorte : lui
    # laisser l'export nominatif reviendrait à contourner ce cloisonnement par
    # une autre route. Ouverture éventuelle à arbitrer par le responsable de
    # traitement et le DPO, pas dans le code.

    @router.get("/export.csv")
    def export_csv(
        request: Request,
        batch_id: str | None = None,
        filiere: str | None = None,
        alertes: str | None = None,
    ) -> Response:
        # A pilote exports over the whole cohort, a referent within their scope:
        # the SQL filter below carries the difference, not the role check.
        identity = guard(request, ROLE_REFERENT, ROLE_PILOTE)
        if isinstance(identity, Response):
            return identity

        with open_session() as session:
            selected_batch = resolve_batch(session, batch_id)
            selected_filiere = resolve_filiere(session, filiere, identity.scope)
            filters = repo.CohortFilters(
                batch_id=selected_batch,
                filiere=selected_filiere,
                alerts_only=_flag(alertes),
                scope=identity.scope,
            )
            total, _ = repo.count_predictions(session, filters)
            if total > settings.export_max_rows:
                return error_page(
                    request,
                    identity,
                    status_code=status.HTTP_400_BAD_REQUEST,
                    heading="Export trop volumineux",
                    message=(
                        f"{total} lignes correspondent à ces critères, au-delà du plafond de "
                        f"{settings.export_max_rows}. Affinez les filtres (filière, alertes "
                        "seules) avant d'exporter."
                    ),
                )
            rows = repo.iter_export_rows(session, filters, max_rows=settings.export_max_rows)
            audit(
                session,
                identity,
                action="portal_export",
                target_type="ingestion_batch",
                target_id=selected_batch,
                reason="Export pseudonymisé transmis au SI scolarité pour rapprochement",
                metadata={
                    "rows": len(rows),
                    "scope": identity.scope if identity.scope is not None else "global",
                    "filiere": selected_filiere,
                    "alerts_only": filters.alerts_only,
                },
            )

        generated_at = _now().isoformat(timespec="seconds")
        buffer = StringIO()
        buffer.write("﻿")  # BOM : filières accentuées lisibles dans Excel FR
        buffer.write("# Portail de restitution - Decrochage L1\n")
        buffer.write("# Finalite : accompagnement pedagogique, aide a la decision humaine\n")
        buffer.write(f"# Lot : {_csv_safe(selected_batch) or 'inconnu'}\n")
        buffer.write(f"# Genere le : {generated_at} par {_csv_safe(identity.username)}\n")
        buffer.write("# Donnees pseudonymisees (HMAC-SHA-256) - usage interne, ne pas rediffuser\n")
        writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "pseudo_id": _csv_safe(row.pseudo_id),
                    "rang": row.rank,
                    "proba_abandon": f"{row.proba_abandon:.6f}",
                    "alerte": row.alerte,
                    "filiere": _csv_safe(row.filiere or ""),
                    "batch_id": _csv_safe(row.batch_id),
                    "model_version": _csv_safe(row.model_version or ""),
                    "threshold": "" if row.threshold is None else f"{row.threshold:.4f}",
                    "generated_at": generated_at,
                }
            )

        stem = FILENAME_UNSAFE.sub("", (selected_batch or "lot"))[:8] or "lot"
        filename = f"cohorte_{stem}_{_now().strftime('%Y%m%d-%H%M%S')}.csv"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        headers.update(NO_STORE_HEADERS)
        # A CSV the browser must not sniff into something renderable.
        headers["X-Content-Type-Options"] = "nosniff"
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers=headers,
        )

    # --- Pilotage ----------------------------------------------------------

    @router.get("/pilotage", response_class=HTMLResponse)
    def pilotage(
        request: Request,
        batch_id: str | None = None,
        seuil: str | None = None,
    ) -> Response:
        identity = guard(request, ROLE_REFERENT, ROLE_PILOTE)
        if isinstance(identity, Response):
            return identity
        bundle = current_bundle(request)

        with open_session() as session:
            batches = repo.list_batches(session)
            selected_batch = resolve_batch(session, batch_id)
            filters = repo.CohortFilters(batch_id=selected_batch, scope=identity.scope)
            snapshot = repo.pilotage_snapshot(
                session, batch_id=selected_batch, scope=identity.scope
            )
            context = repo.model_context(session, filters)
            requested = _float_param(seuil, minimum=0.01, maximum=0.99)
            fallback = (
                context.threshold
                if context.threshold is not None
                else (bundle.threshold if bundle else 0.5)
            )
            effective = (
                requested if requested is not None else min(0.99, max(0.01, float(fallback)))
            )
            simulated_alerts = repo.count_alerts_at_threshold(
                session,
                batch_id=selected_batch,
                scope=identity.scope,
                threshold=effective,
            )
            audit(
                session,
                identity,
                action="portal_view_pilotage",
                target_type="ingestion_batch",
                target_id=selected_batch,
                reason="Consultation des indicateurs agrégés de charge d'accompagnement",
                metadata={
                    "scope": identity.scope if identity.scope is not None else "global",
                    "simulated_threshold": effective,
                },
            )

        ratio = (simulated_alerts / snapshot.total) if snapshot.total else 0.0
        return render(
            request,
            "pilotage.html",
            identity,
            {
                "batches": batches,
                "batch_id": selected_batch,
                "stats": snapshot.stats,
                "total": snapshot.total,
                "hidden_groups": snapshot.hidden_groups,
                "min_group_size": repo.MIN_GROUP_SIZE,
                "small_groups_label": repo.SMALL_GROUPS_LABEL,
                "simulated_threshold": f"{effective:.2f}",
                "simulated_alerts": simulated_alerts,
                "simulated_ratio_label": f"{ratio * 100:.1f} %",
                "histogram_bars": _histogram_bars(snapshot.histogram),
                "histogram_width": HISTOGRAM_WIDTH,
                "histogram_height": HISTOGRAM_HEIGHT,
                "context": batch_context(batches, selected_batch, context),
                "can_export": identity.has_role(ROLE_REFERENT, ROLE_PILOTE),
                "export_url": f"{BASE_PATH}/export.csv?{urlencode({'batch_id': selected_batch or ''})}",
            },
        )

    # --- Conformité --------------------------------------------------------

    @router.get("/conformite", response_class=HTMLResponse)
    def conformite(request: Request) -> Response:
        identity = guard(request, ROLE_AUDITEUR)
        if isinstance(identity, Response):
            return identity
        bundle = current_bundle(request)

        with open_session() as session:
            batches = repo.list_batches(session)
            events = repo.list_audit_events(session)
            action_counts = repo.audit_action_counts(session)
            drift = repo.latest_drift(session)
            # Projected query: the compliance view must never load a scored row.
            context = repo.model_context(
                session, repo.CohortFilters(batch_id=repo.latest_batch_id(session), scope=None)
            )
            audit(
                session,
                identity,
                action="portal_view_compliance",
                target_type="privacy_audit_log",
                target_id=None,
                reason="Contrôle de conformité : accès, conservation et modèle en vigueur",
                metadata={"events_served": len(events)},
            )

        threshold = (
            context.threshold
            if context.threshold is not None
            else (bundle.threshold if bundle else None)
        )
        return render(
            request,
            "conformite.html",
            identity,
            {
                "batches": batches,
                "events": events,
                "action_counts": action_counts,
                "drift": drift,
                "model_version": context.model_version,
                "threshold_label": _threshold_label(threshold),
            },
        )

    # --- À propos du modèle ------------------------------------------------

    @router.get("/a-propos", response_class=HTMLResponse)
    def a_propos(request: Request) -> Response:
        identity = guard(request)
        if isinstance(identity, Response):
            return identity
        bundle = current_bundle(request)
        metadata = dict(bundle.metadata) if bundle and bundle.metadata else {}

        metrics = []
        for key, label in METRIC_LABELS:
            if key not in metadata:
                continue
            value = metadata[key]
            formatted = f"{value:.3f}" if isinstance(value, float) else str(value)
            metrics.append({"label": label, "value": formatted})

        return render(
            request,
            "a_propos.html",
            identity,
            {
                "metrics": metrics,
                "threshold_label": _threshold_label(bundle.threshold if bundle else None),
                "model_version": metadata.get("model_version") or metadata.get("trained_at"),
                "feature_count": len(bundle.feature_cols) if bundle else 0,
                "excluded_groups": _excluded_groups(),
            },
        )

    return router
