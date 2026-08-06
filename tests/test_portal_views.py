"""Behaviour of the portal views: ordering, scope isolation, and reversibility."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from decrochage.api import create_app
from decrochage.persistence import (
    make_session_factory,
    persist_medallion_layers,
    persist_predictions,
)
from decrochage.portal.models import ROLE_PILOTE, ROLE_REFERENT
from decrochage.serving import predict_proba_abandon

from conftest import (
    SeededPortal,
    catalogue_rows,
    create_portal_user,
    login,
    student_rows,
)

PROBA_CELL = re.compile(r"<td>(\d+\.\d)\s*%</td>")


def _probabilities(html: str) -> list[float]:
    return [float(value) for value in PROBA_CELL.findall(html)]


def test_cohort_is_ordered_by_decreasing_risk(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    page = portal_client.get("/portal/cohorte").text
    values = _probabilities(page)

    assert values
    assert values == sorted(values, reverse=True)


def test_context_banner_states_batch_model_and_threshold(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    page = portal_client.get("/portal/cohorte").text

    assert seeded_portal.batch_id[:8] in page
    assert "test-1" in page  # model_version carried by the bundle
    assert "0.30" in page  # decision threshold
    assert "Score d'aide à la décision" in page


def test_scoped_referent_only_sees_their_own_programme(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url,
        "referent-info",
        role=ROLE_REFERENT,
        filieres=["Informatique"],
    )
    login(portal_client, "referent-info")

    page = portal_client.get("/portal/cohorte").text

    assert "Informatique" in page
    assert "Gestion" not in page


def test_out_of_scope_record_returns_404_not_403(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(
        seeded_portal.database_url,
        "referent-info",
        role=ROLE_REFERENT,
        filieres=["Informatique"],
    )
    login(portal_client, "referent-info")
    foreign_pseudo = seeded_portal.pseudo_in("Gestion")

    response = portal_client.get(f"/portal/etudiant/{foreign_pseudo}")

    # 404 and not 403: a scope boundary must not confirm that the record exists.
    assert response.status_code == 404
    assert "introuvable" in response.text


def test_unknown_pseudonym_returns_404(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    response = portal_client.get(f"/portal/etudiant/{'0' * 64}")

    assert response.status_code == 404


def test_risk_sheet_shows_factors_and_the_methodological_caveat(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")
    pseudo = seeded_portal.pseudo_in("Informatique")

    page = portal_client.get(f"/portal/etudiant/{pseudo}").text

    assert "Facteurs aggravants" in page
    assert "Facteurs protecteurs" in page
    assert "ordre d'importance et un sens" in page
    assert "Variables observées" in page
    assert "n'établit aucune causalité" in page


def test_capacity_reports_alert_coverage_without_claiming_recall(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    login(portal_client, "referent01")

    page = portal_client.get("/portal/cohorte?capacite=3").text

    assert "Limite de capacité déclarée (3" in page
    assert "ne mesure pas la performance du modèle" in page


def test_threshold_simulation_does_not_change_the_model_threshold(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "pilote01", role=ROLE_PILOTE)
    login(portal_client, "pilote01")

    portal_client.get("/portal/pilotage?seuil=0.90")

    assert seeded_portal.bundle.threshold == pytest.approx(0.30)
    page = portal_client.get("/portal/pilotage").text
    assert "Seuil en vigueur" in page
    assert "jamais modifié" in page


def test_pilotage_aggregates_every_programme_for_an_unrestricted_scope(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "pilote01", role=ROLE_PILOTE)
    login(portal_client, "pilote01")

    page = portal_client.get("/portal/pilotage").text

    assert "Informatique" in page
    assert "Gestion" in page
    assert "Précaution d'équité" in page


def test_export_is_refused_above_the_configured_ceiling(
    portal_client: TestClient, seeded_portal: SeededPortal, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_portal_user(seeded_portal.database_url, "pilote01", role=ROLE_PILOTE)
    monkeypatch.setenv("DECROCHAGE_PORTAL_EXPORT_MAX_ROWS", "2")
    # Rebuild the app so the new ceiling is picked up by the router settings.
    app = create_app()
    app.state.bundle = seeded_portal.bundle
    client = TestClient(app, follow_redirects=False)
    login(client, "pilote01")

    response = client.get("/portal/export.csv")

    assert response.status_code == 400
    assert "Affinez les filtres" in response.text


def test_longitudinal_history_appears_across_batches(
    portal_client: TestClient, seeded_portal: SeededPortal
) -> None:
    create_portal_user(seeded_portal.database_url, "referent01", role=ROLE_REFERENT)
    students = student_rows()
    scored = predict_proba_abandon(seeded_portal.bundle, students)
    Session = make_session_factory(seeded_portal.database_url)
    with Session() as session:
        # A genuine second ingestion batch, not a re-run of the first one: the
        # view shows one point per batch, so re-scoring the same batch would
        # legitimately stay a single point. The deterministic pseudonym is what
        # links the two batches without any direct identifier.
        second = persist_medallion_layers(
            session,
            students,
            catalogue_rows(),
            source_name="pytest-lot-2",
            source_uri="fixture",
        )
        persist_predictions(session, second.batch_id, students, scored, seeded_portal.bundle)
        session.commit()

    login(portal_client, "referent01")
    pseudo = seeded_portal.pseudo_in("Informatique")
    page = portal_client.get(f"/portal/etudiant/{pseudo}").text

    assert "Évolution entre lots" in page
    assert "Tendance" in page


def test_portal_disabled_leaves_the_inference_api_untouched(
    seeded_portal: SeededPortal, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DECROCHAGE_PORTAL_ENABLED", raising=False)
    monkeypatch.delenv("DECROCHAGE_PORTAL_SECRET", raising=False)
    app = create_app()
    app.state.bundle = seeded_portal.bundle
    app.state.load_error = None
    client = TestClient(app, follow_redirects=False)

    assert app.state.portal_enabled is False
    for path in ["/portal/login", "/portal/cohorte", "/portal/static/portail.css"]:
        assert client.get(path).status_code == 404, path

    # The inference contract is unchanged.
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    response = client.post("/predict", json={"records": student_rows().head(1).to_dict("records")})
    assert response.status_code == 200
    assert set(response.json()["predictions"][0]) == {"proba_abandon", "alerte"}


def test_enabling_the_portal_without_a_secret_stops_the_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DECROCHAGE_PORTAL_ENABLED", "true")
    monkeypatch.delenv("DECROCHAGE_PORTAL_SECRET", raising=False)

    with pytest.raises(ValueError, match="DECROCHAGE_PORTAL_SECRET is required"):
        create_app()
