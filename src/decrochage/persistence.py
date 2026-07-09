"""Database persistence for the medallion architecture.

The local default is SQLite so the certification project remains runnable
without infrastructure. The same SQLAlchemy layer can target another database
through `DECROCHAGE_DATABASE_URL`.
"""

from __future__ import annotations

import json
import os
import hmac
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import numpy as np
import pandas as pd
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from . import features as F
from .preprocessing import clean_raw
from .serving import ModelBundle
from .training import assign_split_labels

DEFAULT_DATABASE_URL = "sqlite:///artifacts/decrochage.db"
DATABASE_URL_ENV = "DECROCHAGE_DATABASE_URL"
PSEUDONYMIZATION_SECRET_ENV = "DECROCHAGE_PSEUDONYMIZATION_SECRET"
RETENTION_DAYS_ENV = "DECROCHAGE_RETENTION_DAYS"
DIRECT_IDENTIFIER_COLS = ("student_id", "id_dossier")
_ENGINE_CACHE: dict[str, Engine] = {}


class Base(DeclarativeBase):
    """Base class for ORM models."""


class IngestionBatch(Base):
    __tablename__ = "ingestion_batch"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="loaded")
    rows_bronze: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_silver: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_gold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class BronzeStudentRaw(Base):
    __tablename__ = "bronze_student_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    parse_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class BronzeCatalogueRaw(Base):
    __tablename__ = "bronze_catalogue_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    parse_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class SilverStudent(Base):
    __tablename__ = "silver_student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(120), index=True)
    id_dossier: Mapped[str | None] = mapped_column(String(120), index=True)
    filiere: Mapped[str | None] = mapped_column(String(120), index=True)
    abandon: Mapped[int | None] = mapped_column(Integer)
    moyenne_finale: Mapped[float | None] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class SilverCatalogue(Base):
    __tablename__ = "silver_catalogue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    filiere: Mapped[str | None] = mapped_column(String(120), index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class GoldTrainingFeature(Base):
    __tablename__ = "gold_training_feature"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    student_id: Mapped[str | None] = mapped_column(String(120), index=True)
    split_set: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    label_abandon: Mapped[int] = mapped_column(Integer, nullable=False)
    features_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class GoldPrediction(Base):
    __tablename__ = "gold_prediction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    student_id: Mapped[str | None] = mapped_column(String(120), index=True)
    proba_abandon: Mapped[float] = mapped_column(Float, nullable=False)
    alerte: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(120))
    threshold: Mapped[float | None] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class GoldDriftReport(Base):
    __tablename__ = "gold_drift_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("ingestion_batch.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    watch_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class PrivacyAuditLog(Base):
    __tablename__ = "privacy_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor: Mapped[str] = mapped_column(String(120), nullable=False, default="system")
    target_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(120), index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


@dataclass(frozen=True)
class MedallionPersistResult:
    """Counts returned after materializing a batch into medallion layers."""

    batch_id: str
    rows_bronze: int
    rows_silver: int
    rows_gold: int


def create_db_engine(database_url: str | None = None):
    """Create a SQLAlchemy engine and ensure local SQLite folders exist."""
    url = resolve_database_url(database_url)
    if url in _ENGINE_CACHE:
        return _ENGINE_CACHE[url]
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True)
    _ENGINE_CACHE[url] = engine
    return engine


def make_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    """Create a configured SQLAlchemy session factory."""
    return sessionmaker(bind=create_db_engine(database_url), expire_on_commit=False, future=True)


def initialize_database(database_url: str | None = None) -> str:
    """Create all persistence tables and return the resolved URL."""
    url = resolve_database_url(database_url)
    engine = create_db_engine(url)
    Base.metadata.create_all(engine)
    return url


def resolve_database_url(database_url: str | None = None) -> str:
    """Resolve the configured database URL."""
    return database_url or os.getenv(DATABASE_URL_ENV, DEFAULT_DATABASE_URL)


def redacted_database_url(database_url: str | None = None) -> str:
    """Return a display-safe database URL."""
    return make_url(resolve_database_url(database_url)).render_as_string(hide_password=True)


def retention_days(retention_days: int | None = None) -> int:
    """Resolve the configured retention period in days."""
    if retention_days is not None:
        return retention_days
    return int(os.getenv(RETENTION_DAYS_ENV, "365"))


def _retention_expires_at(retention_days_value: int | None = None) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=retention_days(retention_days_value))


def _pseudonymization_secret(secret: str | None = None) -> str:
    resolved = secret or os.getenv(PSEUDONYMIZATION_SECRET_ENV)
    if not resolved:
        raise ValueError(
            f"{PSEUDONYMIZATION_SECRET_ENV} is required before persisting student data"
        )
    return resolved


def pseudonymize_identifier(value: Any, *, secret: str | None = None) -> str | None:
    """Pseudonymize a direct identifier with HMAC-SHA-256."""
    if value is None or pd.isna(value):
        return None
    digest = hmac.new(
        _pseudonymization_secret(secret).encode("utf-8"),
        str(value).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def _sanitize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_json(item) for item in value]
    if isinstance(value, (pd.Timestamp, datetime)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, np.generic):
        return _sanitize_json(value.item())
    if isinstance(value, float) and np.isnan(value):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _json_default(value: Any) -> Any:
    sanitized = _sanitize_json(value)
    if sanitized is None:
        return None
    return str(sanitized)


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(_sanitize_json(payload), ensure_ascii=False, default=_json_default)


def _records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.replace({np.nan: None}).to_dict(orient="records")


def _pseudonymize_record(record: dict[str, Any], *, secret: str | None = None) -> dict[str, Any]:
    out = dict(record)
    for col in DIRECT_IDENTIFIER_COLS:
        if col in out:
            out[col] = pseudonymize_identifier(out[col], secret=secret)
    return out


def _pseudonymize_frame(df: pd.DataFrame, *, secret: str | None = None) -> pd.DataFrame:
    out = df.copy()
    for col in DIRECT_IDENTIFIER_COLS:
        if col in out.columns:
            out[col] = out[col].map(lambda value: pseudonymize_identifier(value, secret=secret))
    return out


def _optional_str(row: pd.Series, column: str) -> str | None:
    value = row.get(column)
    if value is None or pd.isna(value):
        return None
    return str(value)


def _optional_float(row: pd.Series, column: str) -> float | None:
    value = row.get(column)
    if value is None or pd.isna(value):
        return None
    return float(value)


def _optional_int(row: pd.Series, column: str) -> int | None:
    value = row.get(column)
    if value is None or pd.isna(value):
        return None
    return int(value)


def _create_batch(
    session: Session,
    *,
    source_name: str,
    source_uri: str | None,
    metadata: dict[str, Any] | None = None,
    retention_days_value: int | None = None,
) -> IngestionBatch:
    batch = IngestionBatch(
        id=str(uuid4()),
        source_name=source_name,
        source_uri=source_uri,
        metadata_json=_to_json(metadata or {}),
        expires_at=_retention_expires_at(retention_days_value),
    )
    session.add(batch)
    session.flush()
    return batch


def _require_batch(session: Session, batch_id: str) -> None:
    if session.get(IngestionBatch, batch_id) is None:
        raise ValueError(f"Unknown ingestion batch id: {batch_id}")


def record_privacy_audit(
    session: Session,
    *,
    action: str,
    target_type: str,
    target_id: str | None,
    reason: str,
    actor: str = "system",
    metadata: dict[str, Any] | None = None,
) -> int:
    """Record an accountability event without storing direct student data."""
    row = PrivacyAuditLog(
        action=action,
        actor=actor,
        target_type=target_type,
        target_id=target_id,
        reason=reason,
        metadata_json=_to_json(metadata or {}),
    )
    session.add(row)
    session.flush()
    return int(row.id)


def _persist_bronze_rows(
    session: Session,
    batch_id: str,
    raw_df: pd.DataFrame,
    catalogue_df: pd.DataFrame,
) -> int:
    for row_number, payload in enumerate(_records(raw_df), start=1):
        session.add(
            BronzeStudentRaw(
                batch_id=batch_id,
                row_number=row_number,
                payload_json=_to_json(payload),
                parse_ok=True,
            )
        )
    for row_number, payload in enumerate(_records(catalogue_df), start=1):
        session.add(
            BronzeCatalogueRaw(
                batch_id=batch_id,
                row_number=row_number,
                payload_json=_to_json(payload),
                parse_ok=True,
            )
        )
    return int(len(raw_df) + len(catalogue_df))


def _build_silver_frames(
    raw_df: pd.DataFrame, catalogue_df: pd.DataFrame, *, secret: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    silver_students = clean_raw(_pseudonymize_frame(raw_df, secret=secret))
    silver_catalogue = catalogue_df.copy()
    if "filiere" in silver_catalogue.columns:
        silver_catalogue["filiere"] = (
            silver_catalogue["filiere"].astype(str).str.strip().str.title()
        )
    return silver_students, silver_catalogue


def _persist_silver_rows(
    session: Session,
    batch_id: str,
    silver_students: pd.DataFrame,
    silver_catalogue: pd.DataFrame,
) -> int:
    for row_number, (_, row) in enumerate(silver_students.iterrows(), start=1):
        session.add(
            SilverStudent(
                batch_id=batch_id,
                row_number=row_number,
                student_id=_optional_str(row, "student_id"),
                id_dossier=_optional_str(row, "id_dossier"),
                filiere=_optional_str(row, "filiere"),
                abandon=_optional_int(row, F.TARGET_CLF),
                moyenne_finale=_optional_float(row, F.TARGET_REG),
                payload_json=_to_json(row.to_dict()),
            )
        )
    for _, row in silver_catalogue.iterrows():
        session.add(
            SilverCatalogue(
                batch_id=batch_id,
                filiere=_optional_str(row, "filiere"),
                payload_json=_to_json(row.to_dict()),
            )
        )
    return int(len(silver_students) + len(silver_catalogue))


def _build_gold_frame(
    silver_students: pd.DataFrame,
    silver_catalogue: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    prepared = F.enrich_with_catalogue(silver_students, silver_catalogue)
    prepared = F.add_engineered_features(prepared)
    gold, feature_cols = F.build_gold_dataset(prepared, include_labels=True)
    for col in F.ID_COLS:
        if col in prepared.columns:
            gold[col] = prepared[col].values
    return gold, feature_cols


def _has_complete_labels(df: pd.DataFrame) -> bool:
    return F.TARGET_CLF in df.columns and df[F.TARGET_CLF].notna().all()


def _persist_gold_features(
    session: Session,
    batch_id: str,
    gold: pd.DataFrame,
    feature_cols: list[str],
    *,
    random_state: int,
) -> int:
    if gold.empty or not _has_complete_labels(gold):
        return 0

    split_labels = assign_split_labels(
        gold[F.TARGET_CLF].astype(int),
        random_state=random_state,
        allow_fallback=True,
    )
    for idx, row in gold.iterrows():
        features = {col: row.get(col) for col in feature_cols}
        session.add(
            GoldTrainingFeature(
                batch_id=batch_id,
                student_id=_optional_str(row, "student_id"),
                split_set=str(split_labels.loc[idx]),
                label_abandon=int(row[F.TARGET_CLF]),
                features_json=_to_json(features),
            )
        )
    return int(len(gold))


def persist_medallion_layers(
    session: Session,
    raw_df: pd.DataFrame,
    catalogue_df: pd.DataFrame,
    *,
    source_name: str = "csv",
    source_uri: str | None = None,
    random_state: int = 42,
    retention_days_value: int | None = None,
    actor: str = "system",
) -> MedallionPersistResult:
    """Persist raw, cleaned and ML-ready data into Bronze/Silver/Gold tables."""
    secret = _pseudonymization_secret()
    batch = _create_batch(
        session,
        source_name=source_name,
        source_uri=source_uri,
        metadata={
            "architecture": "medallion",
            "layers": ["bronze", "silver", "gold"],
            "rgpd": {
                "direct_identifiers": list(DIRECT_IDENTIFIER_COLS),
                "pseudonymization": "HMAC-SHA-256",
                "pseudonymized_from_layer": "silver",
                "bronze_classification": "raw restricted PII",
                "secret_storage": PSEUDONYMIZATION_SECRET_ENV,
            },
        },
        retention_days_value=retention_days_value,
    )

    silver_students, silver_catalogue = _build_silver_frames(raw_df, catalogue_df, secret=secret)
    gold, feature_cols = _build_gold_frame(silver_students, silver_catalogue)

    batch.rows_bronze = _persist_bronze_rows(session, batch.id, raw_df, catalogue_df)
    batch.rows_silver = _persist_silver_rows(session, batch.id, silver_students, silver_catalogue)
    batch.rows_gold = _persist_gold_features(
        session,
        batch.id,
        gold,
        feature_cols,
        random_state=random_state,
    )
    record_privacy_audit(
        session,
        action="medallion_load",
        actor=actor,
        target_type="ingestion_batch",
        target_id=batch.id,
        reason=(
            "Materialisation Bronze brut restreint puis Silver/Gold avec "
            "pseudonymisation HMAC des identifiants directs"
        ),
        metadata={
            "rows_bronze": batch.rows_bronze,
            "rows_silver": batch.rows_silver,
            "rows_gold": batch.rows_gold,
            "expires_at": batch.expires_at,
        },
    )
    session.flush()
    return MedallionPersistResult(
        batch_id=batch.id,
        rows_bronze=batch.rows_bronze,
        rows_silver=batch.rows_silver,
        rows_gold=batch.rows_gold,
    )


def persist_predictions(
    session: Session,
    batch_id: str,
    raw_df: pd.DataFrame,
    scored_df: pd.DataFrame,
    bundle: ModelBundle,
) -> int:
    """Persist model predictions into the Gold prediction table."""
    secret = _pseudonymization_secret()
    _require_batch(session, batch_id)
    if len(raw_df) != len(scored_df):
        raise ValueError("Raw inputs and scored predictions must have the same number of rows")

    model_version = str(
        bundle.metadata.get("model_version") or bundle.metadata.get("trained_at") or ""
    )
    threshold = float(bundle.threshold)
    raw_records = _records(raw_df)

    for idx, scored_row in scored_df.reset_index(drop=True).iterrows():
        raw_payload = (
            _pseudonymize_record(raw_records[idx], secret=secret) if idx < len(raw_records) else {}
        )
        student_id = raw_payload.get("student_id")
        session.add(
            GoldPrediction(
                batch_id=batch_id,
                student_id=str(student_id) if student_id is not None else None,
                proba_abandon=float(scored_row["proba_abandon"]),
                alerte=int(scored_row["alerte"]),
                model_version=model_version or None,
                threshold=threshold,
                payload_json=_to_json({"input": raw_payload, "prediction": scored_row.to_dict()}),
            )
        )
    record_privacy_audit(
        session,
        action="prediction_persist",
        target_type="ingestion_batch",
        target_id=batch_id,
        reason="Persistance de scores de risque pseudonymisés pour accompagnement humain",
        metadata={"rows": int(len(scored_df))},
    )
    session.flush()
    return int(len(scored_df))


def persist_drift_report(
    session: Session,
    batch_id: str,
    report: dict[str, Any],
) -> int:
    """Persist a drift report into the Gold monitoring table."""
    _require_batch(session, batch_id)
    summary = report.get("summary", {})
    row = GoldDriftReport(
        batch_id=batch_id,
        status=str(summary.get("status", "unknown")),
        watch_count=int(summary.get("watch_count", 0)),
        alert_count=int(summary.get("alert_count", 0)),
        report_json=_to_json(report),
    )
    session.add(row)
    record_privacy_audit(
        session,
        action="drift_report_persist",
        target_type="ingestion_batch",
        target_id=batch_id,
        reason="Persistance du monitoring de derive rattache au batch",
        metadata={"status": summary.get("status", "unknown")},
    )
    session.flush()
    return int(row.id)


def purge_expired_batches(
    session: Session, *, now: datetime | None = None, actor: str = "system"
) -> int:
    """Delete expired medallion batches according to the configured retention policy."""
    cutoff = now or datetime.now(timezone.utc)
    expired_ids = [
        row.id
        for row in session.query(IngestionBatch.id)
        .filter(IngestionBatch.expires_at <= cutoff)
        .all()
    ]
    if not expired_ids:
        return 0

    for model in (
        BronzeStudentRaw,
        BronzeCatalogueRaw,
        SilverStudent,
        SilverCatalogue,
        GoldTrainingFeature,
        GoldPrediction,
        GoldDriftReport,
    ):
        session.query(model).filter(model.batch_id.in_(expired_ids)).delete(
            synchronize_session=False
        )
    session.query(IngestionBatch).filter(IngestionBatch.id.in_(expired_ids)).delete(
        synchronize_session=False
    )
    record_privacy_audit(
        session,
        action="retention_purge",
        actor=actor,
        target_type="ingestion_batch",
        target_id=None,
        reason="Suppression des lots expires selon la politique de conservation RGPD",
        metadata={"purged_batches": expired_ids, "cutoff": cutoff},
    )
    session.flush()
    return len(expired_ids)
