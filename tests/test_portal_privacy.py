"""Confidentiality guarantees of the portal.

Same spirit as `test_notebook_privacy.py`: these assertions are deliberately
literal. `gold_prediction.payload_json` stores the whole input record, including
`moyenne_finale` (a leakage target) and quasi-identifiers. Nothing but the
model's own feature columns may ever reach a rendered page.
"""

from __future__ import annotations

from pathlib import Path
import re

from fastapi.testclient import TestClient

from decrochage import features as F
from decrochage.persistence import PrivacyAuditLog, make_session_factory
from decrochage.portal import repository as repo
from decrochage.portal.models import ROLE_AUDITEUR, ROLE_PILOTE, ROLE_REFERENT
from decrochage.portal.routes import EXPORT_COLUMNS, TEMPLATES_DIR

from conftest import SeededPortal, create_portal_user, login

DIRECT_IDENTIFIER_PATTERN = re.compile(r"ETU-\d{5}")
FILE_IDENTIFIER_PATTERN = re.compile(r"DOS-\d{4}")
PSEUDONYM_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _templates() -> list[Path]:
    return sorted(TEMPLATES_DIR.glob("*.html"))


def test_html_responses_carry_their_own_security_headers(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    """The application must not rely on Caddy for its anti-XSS policy.

    A local run, a different ingress or a misordered route would otherwise
    serve student risk assessments with no policy at all.
    """
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    for path in ("/portal/login", "/portal/cohorte"):
        headers = portal_client.get(path).headers
        csp = headers["content-security-policy"]
        assert "default-src 'self'" in csp
        assert "unsafe-inline" not in csp
        assert "frame-ancestors 'none'" in csp
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert "no-store" in headers["cache-control"]


def test_templates_never_disable_autoescaping() -> None:
    for template in _templates():
        source = template.read_text(encoding="utf-8")
        assert "|safe" not in source, template.name
        assert "| safe" not in source, template.name
        assert "autoescape false" not in source, template.name


def test_templates_never_render_the_stored_payload() -> None:
    for template in _templates():
        source = template.read_text(encoding="utf-8")
        assert "payload_json" not in source, template.name
        assert "raw_payload" not in source, template.name


def test_templates_carry_no_inline_style_or_script() -> None:
    for template in _templates():
        source = template.read_text(encoding="utf-8")
        assert 'style="' not in source, template.name
        assert "<style" not in source, template.name
        # The only <script> tag must be the local file reference, never inline code.
        for fragment in source.split("<script")[1:]:
            assert "src=" in fragment.split(">")[0], template.name


def test_scoring_payload_is_restricted_to_model_features(
    seeded_portal: SeededPortal,
) -> None:
    pseudo = seeded_portal.pseudo_in("Informatique")
    Session = make_session_factory(seeded_portal.database_url)

    with Session() as session:
        stored = repo.raw_payload(session, pseudo, seeded_portal.batch_id)
        filtered = repo.scoring_payload(
            session, pseudo, seeded_portal.batch_id, seeded_portal.bundle.feature_cols
        )

    # The stored payload does contain what must never be shown...
    assert "moyenne_finale" in stored["input"]
    assert "student_id" in stored["input"]
    # ...and the whitelist removes all of it.
    forbidden = set(F.LEAKAGE_TARGET_COLS + F.LEAKAGE_TEMPORAL_COLS + F.ID_COLS + F.LEURRE_COLS)
    assert forbidden.isdisjoint(filtered)
    assert set(filtered).issubset(set(seeded_portal.bundle.feature_cols))


def test_no_page_exposes_a_direct_identifier(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url, "referent01", role=ROLE_REFERENT, filieres=["Informatique"]
    )
    create_portal_user(seeded_portal.database_url, "dpo01", role=ROLE_AUDITEUR)
    login(portal_client, "referent01")
    pseudo = seeded_portal.pseudo_in("Informatique")

    pages = [
        portal_client.get("/portal/cohorte").text,
        portal_client.get(f"/portal/etudiant/{pseudo}").text,
        portal_client.get("/portal/pilotage").text,
        portal_client.get("/portal/a-propos").text,
        portal_client.get("/portal/export.csv").text,
    ]
    portal_client.cookies.clear()
    login(portal_client, "dpo01")
    pages.append(portal_client.get("/portal/conformite").text)

    for page in pages:
        assert not DIRECT_IDENTIFIER_PATTERN.search(page)
        assert not FILE_IDENTIFIER_PATTERN.search(page)


def test_risk_sheet_hides_targets_and_excluded_variables(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url, "referent01", role=ROLE_REFERENT, filieres=["Informatique"]
    )
    login(portal_client, "referent01")
    pseudo = seeded_portal.pseudo_in("Informatique")

    page = portal_client.get(f"/portal/etudiant/{pseudo}").text

    # The observed-variables table is built from a whitelist, so no excluded
    # column name can appear as a data label on the sheet.
    observed_section = page.split("Variables observées")[-1]
    for column in F.LEAKAGE_TARGET_COLS + F.LEAKAGE_TEMPORAL_COLS + F.ID_COLS:
        assert column not in observed_section
    assert "couleur_carte_etudiante" not in observed_section
    assert "commentaire_tuteur" not in observed_section


def test_every_consultation_writes_a_pseudonymized_audit_record(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url, "referent01", role=ROLE_REFERENT, filieres=["Informatique"]
    )
    login(portal_client, "referent01")
    pseudo = seeded_portal.pseudo_in("Informatique")

    portal_client.get("/portal/cohorte")
    portal_client.get(f"/portal/etudiant/{pseudo}?motif=revue_commission")
    portal_client.get("/portal/export.csv")

    Session = make_session_factory(seeded_portal.database_url)
    with Session() as session:
        rows = session.query(PrivacyAuditLog).all()
        by_action = {row.action: row for row in rows}

    assert "portal_view_cohort" in by_action
    assert "portal_view_student" in by_action
    assert "portal_export" in by_action

    student_event = by_action["portal_view_student"]
    assert student_event.actor == "referent01"
    assert PSEUDONYM_PATTERN.match(str(student_event.target_id))
    assert student_event.reason == "Revue en commission de suivi"

    for row in rows:
        serialized = f"{row.target_id}{row.reason}{row.metadata_json}"
        assert not DIRECT_IDENTIFIER_PATTERN.search(serialized)


def test_export_carries_exactly_the_agreed_columns(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "pilote01", role=ROLE_PILOTE)
    login(portal_client, "pilote01")

    response = portal_client.get("/portal/export.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=" in response.headers["content-disposition"]

    # The file opens with a UTF-8 BOM so Excel FR reads accented programme names.
    body = response.text
    assert body.startswith("﻿")
    lines = [line for line in body.lstrip("﻿").splitlines() if line and not line.startswith("#")]
    header = lines[0].split(",")
    assert header == EXPORT_COLUMNS
    # No leakage column, no free text, no engineered feature slipped in.
    for column in F.LEAKAGE_TARGET_COLS + F.LEAKAGE_TEMPORAL_COLS + [F.TEXT_COL]:
        assert column not in response.text


def test_export_header_states_purpose_and_non_redistribution(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "pilote01", role=ROLE_PILOTE)
    login(portal_client, "pilote01")

    text = portal_client.get("/portal/export.csv").text

    assert "# Finalite : accompagnement pedagogique" in text
    assert "ne pas rediffuser" in text
    assert "pilote01" in text
    assert seeded_portal.batch_id in text


def test_compliance_view_never_serves_individual_scores(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "dpo01", role=ROLE_AUDITEUR)
    login(portal_client, "dpo01")

    page = portal_client.get("/portal/conformite").text

    assert "Journal de redevabilité" in page
    assert "proba_abandon" not in page
    assert "Probabilité" not in page
