"""Authentication, session and role-based access control of the portal."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from decrochage.api import create_app
from decrochage.persistence import PrivacyAuditLog, make_session_factory
from decrochage.portal.models import ROLE_AUDITEUR, ROLE_PILOTE, ROLE_REFERENT
from decrochage.portal.security import SESSION_COOKIE, issue_session

from conftest import PORTAL_SECRET, TEST_PASSWORD, SeededPortal, create_portal_user, login

PROTECTED_PATHS = [
    "/portal/cohorte",
    "/portal/pilotage",
    "/portal/conformite",
    "/portal/a-propos",
    "/portal/export.csv",
]

GENERIC_LOGIN_ERROR = "Identifiant ou mot de passe incorrect."


def _audit_actions(database_url: str) -> list[str]:
    Session = make_session_factory(database_url)
    with Session() as session:
        return [row.action for row in session.query(PrivacyAuditLog).all()]


@pytest.mark.parametrize("path", PROTECTED_PATHS)
def test_anonymous_access_is_redirected_to_login(portal_client: TestClient, path: str) -> None:
    response = portal_client.get(path)

    assert response.status_code == 303
    assert response.headers["location"].startswith("/portal/login")


def test_login_form_is_reachable_without_a_session(portal_client: TestClient) -> None:
    response = portal_client.get("/portal/login")

    assert response.status_code == 200
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


def test_valid_credentials_open_a_hardened_session(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url, "referent01", role=ROLE_REFERENT, filieres=["Informatique"]
    )

    response = login(portal_client, "referent01")

    assert response.status_code == 303
    cookie_header = response.headers["set-cookie"]
    assert SESSION_COOKIE in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=strict" in cookie_header.replace("samesite", "SameSite")
    assert "portal_login" in _audit_actions(seeded_portal.database_url)


def test_session_cookie_is_secure_unless_explicitly_opted_out(
    seeded_portal: SeededPortal, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The `Secure` flag must be the default, not something a deployment adds.

    The shared `portal_client` fixture opts out so that plain-HTTP tests can
    hold a session; this test rebuilds a client without the opt-out so the
    hardened default stays covered.
    """
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    monkeypatch.setenv("DECROCHAGE_PORTAL_ENABLED", "true")
    monkeypatch.setenv("DECROCHAGE_PORTAL_SECRET", PORTAL_SECRET)
    monkeypatch.delenv("DECROCHAGE_PORTAL_ALLOW_INSECURE_COOKIE", raising=False)
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")

    client = TestClient(create_app(), follow_redirects=False)
    response = login(client, "referent01")

    assert response.status_code == 303
    assert "Secure" in response.headers["set-cookie"].replace("secure", "Secure")


def test_wrong_password_and_unknown_user_return_the_same_message(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)

    wrong_password = login(portal_client, "referent01", "mot-de-passe-errone")
    unknown_user = login(portal_client, "inconnu-du-si", "mot-de-passe-errone")

    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    assert GENERIC_LOGIN_ERROR in wrong_password.text
    assert GENERIC_LOGIN_ERROR in unknown_user.text
    assert _audit_actions(seeded_portal.database_url).count("portal_login_failed") == 2


def test_disabled_account_is_refused_even_with_a_valid_cookie(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url,
        "referent-revoque",
        role=ROLE_REFERENT,
        filieres=["Informatique"],
        disabled=True,
    )
    # A correctly signed cookie, as if issued before the revocation.
    portal_client.cookies.set(
        SESSION_COOKIE, issue_session("referent-revoque", PORTAL_SECRET), path="/portal"
    )

    response = portal_client.get("/portal/cohorte")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/portal/login")


def test_forged_cookie_is_rejected(portal_client: TestClient) -> None:
    portal_client.cookies.set(SESSION_COOKIE, "nimporte.quoi.signature", path="/portal")

    response = portal_client.get("/portal/cohorte")

    assert response.status_code == 303
    assert response.headers["location"].startswith("/portal/login")


def test_cookie_signed_with_another_secret_is_rejected(portal_client: TestClient) -> None:
    portal_client.cookies.set(
        SESSION_COOKIE, issue_session("referent01", "un-autre-secret"), path="/portal"
    )

    response = portal_client.get("/portal/cohorte")

    assert response.status_code == 303


@pytest.mark.parametrize(
    ("role", "allowed", "forbidden"),
    [
        (
            ROLE_REFERENT,
            ["/portal/cohorte", "/portal/pilotage", "/portal/a-propos"],
            ["/portal/conformite"],
        ),
        (
            ROLE_PILOTE,
            ["/portal/pilotage", "/portal/a-propos"],
            ["/portal/cohorte", "/portal/conformite"],
        ),
        (
            ROLE_AUDITEUR,
            ["/portal/conformite", "/portal/a-propos"],
            ["/portal/cohorte", "/portal/pilotage", "/portal/export.csv"],
        ),
    ],
)
def test_role_matrix_is_enforced_route_by_route(
    portal_client: TestClient,
    seeded_portal: SeededPortal,
    role: str,
    allowed: list[str],
    forbidden: list[str],
) -> None:
    create_portal_user(seeded_portal.database_url, f"agent-{role}", role=role)
    login(portal_client, f"agent-{role}")

    for path in allowed:
        assert portal_client.get(path).status_code == 200, path
    for path in forbidden:
        assert portal_client.get(path).status_code == 403, path


def test_home_redirects_each_role_to_its_own_landing_view(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "dpo01", role=ROLE_AUDITEUR)
    login(portal_client, "dpo01")

    response = portal_client.get("/portal/")

    assert response.status_code == 303
    assert response.headers["location"] == "/portal/conformite"


def test_repeated_failures_lock_the_account_temporarily(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)

    statuses = [
        login(portal_client, "referent01", "mauvais-mot-de-passe").status_code for _ in range(6)
    ]

    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429
    # Even the correct password is refused while the lockout window is open.
    assert login(portal_client, "referent01", TEST_PASSWORD).status_code == 429


def test_logout_requires_a_csrf_token(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    without_token = portal_client.post("/portal/logout", data={})

    assert without_token.status_code == 400
    # The session is still valid: a failed CSRF check must not log the user out.
    assert portal_client.get("/portal/cohorte").status_code == 200


def test_logout_with_a_valid_token_clears_the_session(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")
    page = portal_client.get("/portal/cohorte").text
    token = page.split('name="csrf_token" value="')[1].split('"')[0]

    response = portal_client.post("/portal/logout", data={"csrf_token": token})

    assert response.status_code == 303
    portal_client.cookies.clear()
    assert portal_client.get("/portal/cohorte").status_code == 303


def test_login_does_not_follow_an_external_redirect_target(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)

    response = portal_client.post(
        "/portal/login",
        data={
            "username": "referent01",
            "password": TEST_PASSWORD,
            "next": "https://exfiltration.invalid/collecte",
        },
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/portal/"
