import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from decrochage.persistence import (
    BronzeCatalogueRaw,
    BronzeStudentRaw,
    GoldDriftReport,
    GoldPrediction,
    GoldTrainingFeature,
    IngestionBatch,
    PrivacyAuditLog,
    SilverCatalogue,
    SilverStudent,
    initialize_database,
    make_session_factory,
    persist_drift_report,
    persist_medallion_layers,
    persist_predictions,
    pseudonymize_identifier,
    purge_expired_batches,
    redacted_database_url,
)
from decrochage.serving import ModelBundle


class DummyPipeline:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        proba = np.where(X["taux_rendu_devoirs"].fillna(0) >= 0.5, 0.2, 0.8)
        return np.column_stack([1 - proba, proba])


def _database_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'decrochage.db'}"


def _students() -> pd.DataFrame:
    rows = []
    for idx in range(6):
        rows.append(
            {
                "student_id": f"stu-{idx}",
                "id_dossier": f"dos-{idx}",
                "filiere": "informatique" if idx % 2 else "Gestion",
                "abandon": idx % 2,
                "moyenne_finale": 8.0 + idx,
                "moyenne_partiels_s1": 7.0 + idx,
                "nb_ue_validees_s1": idx,
                "nb_devoirs_total": 10,
                "nb_devoirs_rendus": 2 + idx,
                "connexions_lms_30j": 1 + idx,
                "heures_lms_total": 4 + idx,
                "ressources_consultees": 5 + idx,
                "commentaire_tuteur": "" if idx % 2 else "Signal faible",
                "date_inscription": f"2024-09-0{idx + 1}",
                "distance_domicile_km": f"{10 + idx},5 km",
                "taux_presence_pct": f"{70 + idx}%",
            }
        )
    return pd.DataFrame(rows)


def _catalogue() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"filiere": "Informatique", "faculte": "Sciences", "capacite": 120},
            {"filiere": "Gestion", "faculte": "Economie", "capacite": 90},
        ]
    )


@pytest.fixture(autouse=True)
def _pseudonymization_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DECROCHAGE_PSEUDONYMIZATION_SECRET", "unit-test-secret")


def test_initialize_database_and_persist_medallion_layers(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        result = persist_medallion_layers(session, _students(), _catalogue())

        assert result.rows_bronze == 8
        assert result.rows_silver == 8
        assert result.rows_gold == 6
        assert session.query(BronzeStudentRaw).count() == 6
        assert session.query(BronzeCatalogueRaw).count() == 2
        assert session.query(SilverStudent).count() == 6
        assert session.query(SilverCatalogue).count() == 2
        assert session.query(GoldTrainingFeature).count() == 6
        assert session.query(PrivacyAuditLog).filter_by(action="medallion_load").count() == 1


def test_gold_features_exclude_leakage_columns(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        persist_medallion_layers(session, _students(), _catalogue())
        gold_row = session.query(GoldTrainingFeature).first()

    features = json.loads(gold_row.features_json)
    assert "abandon" not in features
    assert "moyenne_finale" not in features
    assert "moyenne_partiels_s1" not in features
    assert "nb_ue_validees_s1" not in features
    assert "student_id" not in features
    assert gold_row.split_set in {"train", "validation", "test"}


def test_bronze_keeps_raw_identifiers_and_silver_gold_are_pseudonymized(
    tmp_path: Path,
) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        result = persist_medallion_layers(session, _students(), _catalogue())
        bronze_payload = json.loads(session.query(BronzeStudentRaw).first().payload_json)
        silver_row = session.query(SilverStudent).first()
        gold_row = session.query(GoldTrainingFeature).first()

    expected_student = pseudonymize_identifier("stu-0")
    assert bronze_payload["student_id"] == "stu-0"
    assert bronze_payload["id_dossier"] == "dos-0"
    assert silver_row.student_id == expected_student
    assert silver_row.id_dossier == pseudonymize_identifier("dos-0")
    assert gold_row.student_id == expected_student
    assert result.rows_gold == 6


def test_persist_predictions_and_drift_report(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        result = persist_medallion_layers(session, _students(), _catalogue())
        bundle = ModelBundle(
            pipeline=DummyPipeline(),
            feature_cols=["taux_rendu_devoirs"],
            threshold=0.5,
            metadata={"model_version": "test"},
        )
        scored = pd.DataFrame({"proba_abandon": [0.2, 0.8], "alerte": [0, 1]})

        persisted = persist_predictions(
            session, result.batch_id, _students().head(2), scored, bundle
        )
        report_id = persist_drift_report(
            session,
            result.batch_id,
            {"summary": {"status": "watch", "watch_count": 1, "alert_count": 0}, "features": []},
        )

        assert persisted == 2
        assert report_id > 0
        assert session.query(GoldPrediction).count() == 2
        assert session.query(GoldDriftReport).count() == 1
        prediction_payload = json.loads(session.query(GoldPrediction).first().payload_json)
        assert "stu-0" not in json.dumps(prediction_payload)
        assert prediction_payload["input"]["student_id"] == pseudonymize_identifier("stu-0")


def test_persist_predictions_rejects_unknown_batch(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        bundle = ModelBundle(pipeline=DummyPipeline(), feature_cols=[], threshold=0.5)
        scored = pd.DataFrame({"proba_abandon": [0.8], "alerte": [1]})

        with pytest.raises(ValueError, match="Unknown ingestion batch id"):
            persist_predictions(session, "missing-batch", _students().head(1), scored, bundle)


def test_database_url_is_redacted_for_display() -> None:
    safe_url = redacted_database_url("postgresql://user:secret@example.test:5432/db")

    assert "secret" not in safe_url
    assert "***" in safe_url


def test_persisting_student_data_requires_pseudonymization_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DECROCHAGE_PSEUDONYMIZATION_SECRET", raising=False)
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        with pytest.raises(ValueError, match="DECROCHAGE_PSEUDONYMIZATION_SECRET"):
            persist_medallion_layers(session, _students(), _catalogue())


def test_sqlite_memory_database_reuses_initialized_engine() -> None:
    url = "sqlite:///:memory:"
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        result = persist_medallion_layers(session, _students(), _catalogue())

        assert result.rows_gold == 6
        assert session.query(GoldTrainingFeature).count() == 6


def test_unlabeled_batch_persists_bronze_and_silver_without_gold(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)
    students = _students().drop(columns=["abandon"])

    Session = make_session_factory(url)
    with Session() as session:
        result = persist_medallion_layers(session, students, _catalogue())

        assert result.rows_bronze == 8
        assert result.rows_silver == 8
        assert result.rows_gold == 0
        assert session.query(SilverStudent).count() == 6
        assert session.query(GoldTrainingFeature).count() == 0


def test_purge_expired_batches_removes_sensitive_rows(tmp_path: Path) -> None:
    url = _database_url(tmp_path)
    initialize_database(url)

    Session = make_session_factory(url)
    with Session() as session:
        persist_medallion_layers(
            session,
            _students(),
            _catalogue(),
            retention_days_value=-1,
        )
        purged = purge_expired_batches(session)

        assert purged == 1
        assert session.query(IngestionBatch).count() == 0
        assert session.query(BronzeStudentRaw).count() == 0
        assert session.query(SilverStudent).count() == 0
        assert session.query(GoldTrainingFeature).count() == 0
        assert session.query(PrivacyAuditLog).filter_by(action="retention_purge").count() == 1
