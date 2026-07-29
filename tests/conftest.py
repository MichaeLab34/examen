"""Shared fixtures for the restitution portal tests.

The rest of the suite keeps its self-contained style; the portal needs a seeded
database, a real linear bundle and an authenticated client, which would be
duplicated four times otherwise. No fixture here is `autouse`, so existing test
modules are unaffected.

The password below is test material for a throwaway SQLite file. The application
ships no default account and never accepts a password as a CLI argument.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from decrochage.api import create_app
from decrochage.persistence import (
    initialize_database,
    make_session_factory,
    persist_medallion_layers,
    persist_predictions,
    pseudonymize_identifier,
)
from decrochage.portal.models import PortalUser, normalize_scope
from decrochage.portal.security import hash_password
from decrochage.serving import ModelBundle, predict_proba_abandon
from decrochage.training import build_preprocessor, prepare_training_frame

TEST_PASSWORD = "portail-test-2026"
PSEUDONYMIZATION_SECRET = "portal-unit-test-secret"
PORTAL_SECRET = "portal-unit-test-session-secret"

FILIERES = ("Informatique", "Gestion")


def student_rows(count: int = 12) -> pd.DataFrame:
    """Build a small deterministic cohort covering two programmes."""
    rows = []
    for index in range(count):
        rows.append(
            {
                "student_id": f"ETU-{10000 + index}",
                "id_dossier": f"DOS-{5000 + index}",
                "filiere": FILIERES[index % 2],
                "abandon": index % 3 == 0,
                "moyenne_finale": 6.0 + (index % 10),
                "moyenne_partiels_s1": 7.0 + (index % 8),
                "nb_ue_validees_s1": index % 6,
                "age": 18 + (index % 4),
                "sexe": "F" if index % 2 else "M",
                "boursier": "oui" if index % 3 else "non",
                "nb_devoirs_total": 10,
                "nb_devoirs_rendus": index % 11,
                "connexions_lms_30j": 1 + (index % 15),
                "heures_lms_total": 2.0 + index,
                "ressources_consultees": index * 2,
                "heures_travail_remunere": index % 20,
                "commentaire_tuteur": "" if index % 2 else "Absences repetees",
                "date_inscription": f"2024-09-{(index % 27) + 1:02d}",
                "distance_domicile_km": f"{5 + index},5 km",
                "taux_presence_pct": f"{50 + (index % 50)}%",
                "groupe_td": f"TD{index % 4}",
                "couleur_carte_etudiante": "bleue",
                "jour_inscription": "lundi",
            }
        )
    frame = pd.DataFrame(rows)
    frame["abandon"] = frame["abandon"].astype(int)
    return frame


def catalogue_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "filiere": "Informatique",
                "faculte": "Sciences",
                "capacite_accueil": 120,
                "taux_reussite_moyen": 0.62,
            },
            {
                "filiere": "Gestion",
                "faculte": "Economie",
                "capacite_accueil": 90,
                "taux_reussite_moyen": 0.71,
            },
        ]
    )


def build_linear_bundle(
    students: pd.DataFrame, catalogue: pd.DataFrame, *, threshold: float = 0.3
) -> ModelBundle:
    """Train a real `pre`/`clf` pipeline so explanations can be checked exactly."""
    prepared = prepare_training_frame(students, catalogue)
    from decrochage import features as F

    gold, feature_cols = F.build_gold_dataset(prepared, include_labels=True)
    X = gold[feature_cols]
    y = gold[F.TARGET_CLF].astype(int)
    pipeline = Pipeline(
        [
            ("pre", build_preprocessor(X)),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )
    pipeline.fit(X, y)
    return ModelBundle(
        pipeline=pipeline,
        feature_cols=feature_cols,
        threshold=threshold,
        catalogue=catalogue,
        metadata={
            "model_version": "test-1",
            "auc_test": 0.87,
            "recall_test": 0.8,
            "n_features": len(feature_cols),
        },
    )


@dataclass(frozen=True)
class SeededPortal:
    """Everything a portal test needs to address seeded data."""

    database_url: str
    batch_id: str
    bundle: ModelBundle
    students: pd.DataFrame

    def pseudo_for(self, student_id: str) -> str:
        return pseudonymize_identifier(student_id, secret=PSEUDONYMIZATION_SECRET)

    def pseudo_in(self, filiere: str) -> str:
        match = self.students.loc[self.students["filiere"] == filiere, "student_id"].iloc[0]
        return self.pseudo_for(str(match))


@pytest.fixture
def portal_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Create an isolated SQLite database and point the whole stack at it."""
    url = f"sqlite:///{tmp_path / 'portal.db'}"
    monkeypatch.setenv("DECROCHAGE_PSEUDONYMIZATION_SECRET", PSEUDONYMIZATION_SECRET)
    monkeypatch.setenv("DECROCHAGE_DATABASE_URL", url)
    initialize_database(url)
    return url


@pytest.fixture
def seeded_portal(portal_database: str) -> SeededPortal:
    """Seed medallion layers plus persisted predictions from a real bundle."""
    students = student_rows()
    catalogue = catalogue_rows()
    bundle = build_linear_bundle(students, catalogue)
    scored = predict_proba_abandon(bundle, students)

    Session = make_session_factory(portal_database)
    with Session() as session:
        result = persist_medallion_layers(
            session, students, catalogue, source_name="pytest", source_uri="fixture"
        )
        persist_predictions(session, result.batch_id, students, scored, bundle)
        session.commit()

    return SeededPortal(
        database_url=portal_database,
        batch_id=result.batch_id,
        bundle=bundle,
        students=students,
    )


def create_portal_user(
    database_url: str,
    username: str,
    *,
    role: str,
    filieres: list[str] | None = None,
    password: str = TEST_PASSWORD,
    disabled: bool = False,
) -> None:
    """Insert a portal account directly, mirroring what the CLI does."""
    from datetime import datetime, timezone

    Session = make_session_factory(database_url)
    with Session() as session:
        session.add(
            PortalUser(
                username=username,
                display_name=None,
                role=role,
                scope_filieres=normalize_scope(filieres),
                password_hash=hash_password(password),
                must_change_password=False,
                disabled_at=datetime.now(timezone.utc) if disabled else None,
            )
        )
        session.commit()


@pytest.fixture
def portal_client(seeded_portal: SeededPortal, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Return a client on an app with the portal enabled and a bundle loaded.

    The insecure-cookie opt-out is set because `TestClient` speaks plain HTTP:
    httpx would refuse to send back a `Secure` cookie, and every authenticated
    test would silently degrade into an anonymous one. The secure-by-default
    behaviour itself is asserted in `test_portal_auth`, which builds its own
    client without this variable.
    """
    monkeypatch.setenv("DECROCHAGE_PORTAL_ENABLED", "true")
    monkeypatch.setenv("DECROCHAGE_PORTAL_SECRET", PORTAL_SECRET)
    monkeypatch.setenv("DECROCHAGE_PORTAL_ALLOW_INSECURE_COOKIE", "true")
    monkeypatch.setenv("DECROCHAGE_MODEL_PATH", "missing/model.joblib")
    app = create_app()
    app.state.bundle = seeded_portal.bundle
    app.state.load_error = None
    return TestClient(app, follow_redirects=False)


def login(client: TestClient, username: str, password: str = TEST_PASSWORD):
    """Submit the login form and return the raw response."""
    return client.post(
        "/portal/login",
        data={"username": username, "password": password},
    )
