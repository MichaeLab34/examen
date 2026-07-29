"""Read-only queries backing the portal views.

Four invariants govern this module:

1. **Scope filtering happens in SQL, never in a template.** A referent is bound
   to a list of programmes; the filter is a join condition, so an out-of-scope
   pseudonym simply does not exist for that user. A scope of `[]` (unreadable
   stored value) matches nothing — fail-closed.
2. **Programme names come from `silver_student`.** `gold_prediction` has no
   `filiere` column and `silver_student.filiere` is already indexed. A restricted
   scope uses an INNER JOIN, an unrestricted one a LEFT JOIN so nothing is
   silently dropped for a programme lead.
3. **One row per student.** `silver_student` is de-duplicated by `clean_raw`
   while `gold_prediction` is not, and a scoring run can be replayed on the same
   batch. Every query therefore keeps only the latest prediction per
   `(batch_id, student_id)`; otherwise counts would report joined rows rather
   than students.
4. **The portal never reads `payload_json` wholesale.** `scoring_payload`
   intersects with the model's feature columns *and* subtracts the locked
   perimeter, because that payload also carries `moyenne_finale` — a leakage
   target that must never reach a screen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from statistics import median, quantiles
from typing import Any

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from .. import features as F
from ..persistence import (
    GoldDriftReport,
    GoldPrediction,
    IngestionBatch,
    PrivacyAuditLog,
    SilverStudent,
)

PSEUDO_DISPLAY_LENGTH = 12

# Minimum head-count before per-programme indicators are published. Below this,
# an aggregate is effectively individual: with one student in a programme, the
# median *is* that student's score.
MIN_GROUP_SIZE = 5
SMALL_GROUPS_LABEL = "Filières à faible effectif (regroupées)"
UNKNOWN_FILIERE_LABEL = "Filière non renseignée"

# Columns that must never leave the database through a restitution screen,
# whatever the bundle claims as its feature list.
FORBIDDEN_RESTITUTION_COLS: frozenset[str] = frozenset(
    F.LEAKAGE_TARGET_COLS
    + F.LEAKAGE_TEMPORAL_COLS
    + F.ID_COLS
    + F.LEURRE_COLS
    + [F.TARGET_CLF, F.TARGET_REG, F.TEXT_COL]
)

_MISSING_TEXT = {"", "nan", "none", "null", "na"}


@dataclass(frozen=True)
class PredictionRow:
    """One scored student, as shown in the cohort table."""

    pseudo_id: str
    filiere: str | None
    proba_abandon: float
    alerte: int
    batch_id: str
    model_version: str | None
    threshold: float | None
    created_at: datetime | None
    rank: int = 0

    @property
    def short_pseudo(self) -> str:
        return self.pseudo_id[:PSEUDO_DISPLAY_LENGTH]

    @property
    def proba_pct(self) -> str:
        return f"{self.proba_abandon * 100:.1f} %"


@dataclass(frozen=True)
class CohortPage:
    """A page of the prioritized cohort plus the banner counters."""

    rows: list[PredictionRow]
    total: int
    alert_count: int
    page: int
    page_size: int

    @property
    def page_count(self) -> int:
        if self.page_size <= 0:
            return 1
        return max(1, -(-self.total // self.page_size))

    @property
    def has_previous(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.page_count


@dataclass(frozen=True)
class FiliereStat:
    """Aggregated risk indicators for one programme.

    The upper decile stands in for the maximum probability the PRD's screen
    sketch first suggested: a maximum *is* one student's score, whereas a
    quantile over a group of at least `MIN_GROUP_SIZE` still answers the only
    question this view asks — how concentrated the risk is at the top.
    """

    filiere: str
    effectif: int
    alertes: int
    proba_mediane: float
    proba_decile_sup: float
    aggregated: bool = False

    @property
    def taux_alerte(self) -> float:
        return (self.alertes / self.effectif) if self.effectif else 0.0


@dataclass(frozen=True)
class PilotageSnapshot:
    """Everything the pilotage view needs, computed in a single pass."""

    total: int
    stats: list[FiliereStat]
    histogram: list[tuple[float, float, int]]
    hidden_groups: int


@dataclass(frozen=True)
class BatchInfo:
    """Ingestion batch metadata, including its retention deadline."""

    batch_id: str
    source_name: str
    rows_bronze: int
    rows_silver: int
    rows_gold: int
    created_at: datetime | None
    expires_at: datetime | None

    def days_left(self, *, now: datetime) -> int | None:
        if self.expires_at is None:
            return None
        reference = self.expires_at
        if reference.tzinfo is None and now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        elif reference.tzinfo is not None and now.tzinfo is None:
            reference = reference.replace(tzinfo=None)
        return (reference - now).days

    @property
    def short_id(self) -> str:
        return self.batch_id[:8]


@dataclass(frozen=True)
class AuditEvent:
    """One accountability record, as displayed to the data-protection officer."""

    action: str
    actor: str
    target_type: str
    target_id: str | None
    reason: str
    created_at: datetime | None

    @property
    def short_target(self) -> str:
        if not self.target_id:
            return "—"
        return self.target_id[:PSEUDO_DISPLAY_LENGTH]


@dataclass(frozen=True)
class DriftSummary:
    """Latest persisted drift report summary."""

    status: str
    watch_count: int
    alert_count: int
    created_at: datetime | None


@dataclass(frozen=True)
class ModelContext:
    """Model version and threshold in force for a batch, without any score."""

    model_version: str | None
    threshold: float | None


@dataclass(frozen=True)
class CohortFilters:
    """Normalized query parameters for the cohort view."""

    batch_id: str | None = None
    filiere: str | None = None
    alerts_only: bool = False
    page: int = 1
    scope: list[str] | None = field(default=None)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _MISSING_TEXT:
        return None
    return text


def _normalize_filiere(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    return cleaned.title() if cleaned else None


def _latest_prediction_ids(session: Session, batch_id: str | None):
    """Scalar subquery yielding the latest prediction id per (batch, student).

    Rows whose `student_id` is NULL are grouped together; such records carry no
    usable pseudonym and cannot be opened as a risk sheet anyway.
    """
    query = session.query(func.max(GoldPrediction.id))
    if batch_id:
        query = query.filter(GoldPrediction.batch_id == batch_id)
    return query.group_by(GoldPrediction.batch_id, GoldPrediction.student_id).scalar_subquery()


def _scoped_query(session: Session, scope: list[str] | None, batch_id: str | None, *entities):
    """Return a de-duplicated, scope-restricted query over predictions."""
    join_condition = and_(
        SilverStudent.student_id == GoldPrediction.student_id,
        SilverStudent.batch_id == GoldPrediction.batch_id,
    )
    query = (
        session.query(*entities)
        if entities
        else session.query(GoldPrediction, SilverStudent.filiere)
    )
    if scope is None:
        query = query.outerjoin(SilverStudent, join_condition)
    else:
        # Fail-closed: an empty scope matches nothing, and without a Silver row
        # we cannot prove the programme, so the record stays invisible.
        query = query.join(SilverStudent, join_condition).filter(SilverStudent.filiere.in_(scope))
    return query.filter(GoldPrediction.id.in_(_latest_prediction_ids(session, batch_id)))


def _apply_filters(query, filters: CohortFilters):
    if filters.batch_id:
        query = query.filter(GoldPrediction.batch_id == filters.batch_id)
    filiere = _normalize_filiere(filters.filiere)
    if filiere:
        query = query.filter(SilverStudent.filiere == filiere)
    if filters.alerts_only:
        query = query.filter(GoldPrediction.alerte == 1)
    return query


def _filtered(session: Session, filters: CohortFilters, *entities):
    return _apply_filters(
        _scoped_query(session, filters.scope, filters.batch_id, *entities), filters
    )


def _to_row(prediction: GoldPrediction, filiere: str | None, rank: int) -> PredictionRow:
    return PredictionRow(
        pseudo_id=str(prediction.student_id or ""),
        filiere=_clean_text(filiere),
        proba_abandon=float(prediction.proba_abandon),
        alerte=int(prediction.alerte),
        batch_id=str(prediction.batch_id),
        model_version=_clean_text(prediction.model_version),
        threshold=prediction.threshold,
        created_at=prediction.created_at,
        rank=rank,
    )


def latest_batch_id(session: Session) -> str | None:
    """Return the most recent batch that actually carries predictions."""
    row = (
        session.query(GoldPrediction.batch_id)
        .order_by(GoldPrediction.created_at.desc(), GoldPrediction.id.desc())
        .first()
    )
    return str(row[0]) if row else None


def batch_exists(session: Session, batch_id: str) -> bool:
    """Return True when `batch_id` designates a known ingestion batch."""
    return (
        session.query(IngestionBatch.id).filter(IngestionBatch.id == batch_id).first() is not None
    )


def list_batches(session: Session, *, limit: int = 50) -> list[BatchInfo]:
    """Return ingestion batches, most recent first."""
    rows = (
        session.query(IngestionBatch).order_by(IngestionBatch.created_at.desc()).limit(limit).all()
    )
    return [
        BatchInfo(
            batch_id=str(row.id),
            source_name=str(row.source_name),
            rows_bronze=int(row.rows_bronze),
            rows_silver=int(row.rows_silver),
            rows_gold=int(row.rows_gold),
            created_at=row.created_at,
            expires_at=row.expires_at,
        )
        for row in rows
    ]


def available_filieres(session: Session, scope: list[str] | None) -> list[str]:
    """Return the programmes the user may filter on."""
    query = session.query(SilverStudent.filiere).distinct()
    if scope is not None:
        query = query.filter(SilverStudent.filiere.in_(scope))
    values = [_clean_text(row[0]) for row in query.all()]
    return sorted({value for value in values if value})


def model_context(session: Session, filters: CohortFilters) -> ModelContext:
    """Return the model version and threshold in force, without reading a score."""
    row = (
        _filtered(session, filters, GoldPrediction.model_version, GoldPrediction.threshold)
        .order_by(GoldPrediction.id.desc())
        .first()
    )
    if row is None:
        return ModelContext(model_version=None, threshold=None)
    return ModelContext(model_version=_clean_text(row[0]), threshold=row[1])


def count_predictions(session: Session, filters: CohortFilters) -> tuple[int, int]:
    """Return (total, alert_count) for the current filters, in one query."""
    row = _filtered(
        session,
        filters,
        func.count(GoldPrediction.id),
        func.coalesce(func.sum(GoldPrediction.alerte), 0),
    ).one()
    return int(row[0] or 0), int(row[1] or 0)


def list_predictions(
    session: Session,
    filters: CohortFilters,
    *,
    page_size: int,
) -> CohortPage:
    """Return one page of the cohort, ordered by descending risk."""
    total, alerts = count_predictions(session, filters)
    page = max(1, filters.page)
    offset = (page - 1) * page_size

    records = (
        _filtered(session, filters)
        .order_by(GoldPrediction.proba_abandon.desc(), GoldPrediction.id.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    rows = [
        _to_row(prediction, filiere, offset + index + 1)
        for index, (prediction, filiere) in enumerate(records)
    ]
    return CohortPage(
        rows=rows,
        total=total,
        alert_count=alerts,
        page=page,
        page_size=page_size,
    )


def iter_export_rows(
    session: Session,
    filters: CohortFilters,
    *,
    max_rows: int,
) -> list[PredictionRow]:
    """Return up to `max_rows` rows, ordered by descending risk."""
    records = (
        _filtered(session, filters)
        .order_by(GoldPrediction.proba_abandon.desc(), GoldPrediction.id.asc())
        .limit(max(0, max_rows))
        .all()
    )
    return [
        _to_row(prediction, filiere, index + 1)
        for index, (prediction, filiere) in enumerate(records)
    ]


def count_alerts_in_top(
    session: Session,
    filters: CohortFilters,
    *,
    top_k: int,
) -> int:
    """Count alerts among the `top_k` highest-risk records, without loading them."""
    if top_k <= 0:
        return 0
    rows = (
        _filtered(session, filters, GoldPrediction.alerte)
        .order_by(GoldPrediction.proba_abandon.desc(), GoldPrediction.id.asc())
        .limit(top_k)
        .all()
    )
    return sum(int(row[0]) for row in rows)


def get_prediction(
    session: Session,
    pseudo_id: str,
    *,
    scope: list[str] | None,
    batch_id: str | None = None,
) -> PredictionRow | None:
    """Return the most recent prediction for `pseudo_id`, or None when out of scope."""
    filters = CohortFilters(batch_id=batch_id, scope=scope)
    record = (
        _filtered(session, filters)
        .filter(GoldPrediction.student_id == pseudo_id)
        .order_by(GoldPrediction.created_at.desc(), GoldPrediction.id.desc())
        .first()
    )
    if record is None:
        return None
    prediction, filiere = record
    return _to_row(prediction, filiere, 0)


def student_history(
    session: Session,
    pseudo_id: str,
    *,
    scope: list[str] | None,
) -> list[PredictionRow]:
    """Return every retained prediction for `pseudo_id`, oldest first.

    The HMAC pseudonym is deterministic across batches, which is what makes a
    longitudinal view possible without ever handling a direct identifier.
    """
    records = (
        _scoped_query(session, scope, None)
        .filter(GoldPrediction.student_id == pseudo_id)
        .order_by(GoldPrediction.created_at.asc(), GoldPrediction.id.asc())
        .all()
    )
    return [_to_row(prediction, filiere, 0) for prediction, filiere in records]


def raw_payload(session: Session, pseudo_id: str, batch_id: str) -> dict[str, Any]:
    """Return the stored prediction payload for one record (internal use only)."""
    record = (
        session.query(GoldPrediction.payload_json)
        .filter(
            GoldPrediction.student_id == pseudo_id,
            GoldPrediction.batch_id == batch_id,
        )
        .order_by(GoldPrediction.id.desc())
        .first()
    )
    if record is None or not record[0]:
        return {}
    try:
        payload = json.loads(record[0])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def scoring_payload(
    session: Session,
    pseudo_id: str,
    batch_id: str,
    feature_cols: list[str],
) -> dict[str, Any]:
    """Return the stored input restricted to displayable model features.

    Two guards, deliberately redundant: intersect with the bundle's own feature
    list, then subtract the locked perimeter. The second one matters because
    `feature_cols` comes from a serialized artifact loaded from a path or an
    MLflow alias — it is not, by itself, a trustworthy whitelist.
    """
    payload = raw_payload(session, pseudo_id, batch_id)
    stored_input = payload.get("input")
    if not isinstance(stored_input, dict):
        return {}
    return {
        column: stored_input[column]
        for column in feature_cols
        if column in stored_input and column not in FORBIDDEN_RESTITUTION_COLS
    }


def pilotage_snapshot(
    session: Session,
    *,
    batch_id: str | None,
    scope: list[str] | None,
    bins: int = 10,
) -> PilotageSnapshot:
    """Aggregate per-programme indicators and the probability histogram.

    A single projected query (three scalars per row) feeds both, instead of
    instantiating full ORM objects — `payload_json` alone is ~1.5 kB per student.
    Medians are computed in Python because SQLite has no percentile function.
    """
    filters = CohortFilters(batch_id=batch_id, scope=scope)
    records = _filtered(
        session,
        filters,
        GoldPrediction.proba_abandon,
        GoldPrediction.alerte,
        SilverStudent.filiere,
    ).all()

    grouped: dict[str, list[tuple[float, int]]] = {}
    probabilities: list[float] = []
    for proba, alerte, filiere in records:
        value = float(proba)
        probabilities.append(value)
        key = _clean_text(filiere) or UNKNOWN_FILIERE_LABEL
        grouped.setdefault(key, []).append((value, int(alerte)))

    published: list[FiliereStat] = []
    pooled: list[tuple[float, int]] = []
    hidden_groups = 0
    for key, values in grouped.items():
        if len(values) < MIN_GROUP_SIZE:
            # Below the minimum head-count an aggregate identifies individuals.
            pooled.extend(values)
            hidden_groups += 1
            continue
        probas = [proba for proba, _ in values]
        published.append(
            FiliereStat(
                filiere=key,
                effectif=len(values),
                alertes=sum(alerte for _, alerte in values),
                proba_mediane=float(median(probas)),
                proba_decile_sup=_upper_decile(probas),
            )
        )
    if len(pooled) >= MIN_GROUP_SIZE:
        probas = [proba for proba, _ in pooled]
        published.append(
            FiliereStat(
                filiere=SMALL_GROUPS_LABEL,
                effectif=len(pooled),
                alertes=sum(alerte for _, alerte in pooled),
                proba_mediane=float(median(probas)),
                proba_decile_sup=_upper_decile(probas),
                aggregated=True,
            )
        )
    # When the pool itself stays below the threshold, pooling protects nothing:
    # the residue is dropped rather than published. `hidden_groups` already
    # counts each programme it contains.

    return PilotageSnapshot(
        total=len(probabilities),
        stats=sorted(published, key=lambda item: (item.aggregated, -item.taux_alerte)),
        histogram=_histogram(probabilities, bins=bins),
        hidden_groups=hidden_groups,
    )


def _upper_decile(values: list[float]) -> float:
    """Return the 90th percentile of `values`, falling back on the median.

    `quantiles` needs at least two points; groups reaching here always have
    `MIN_GROUP_SIZE`, but the fallback keeps the function total rather than
    letting a future caller raise `StatisticsError` inside a request.
    """
    if not values:
        return 0.0
    if len(values) < 2:
        return float(values[0])
    return float(quantiles(values, n=10)[8])


def _histogram(values: list[float], *, bins: int) -> list[tuple[float, float, int]]:
    width = 1.0 / bins
    buckets: list[tuple[float, float, int]] = []
    for index in range(bins):
        lower = index * width
        upper = lower + width
        if index == bins - 1:
            count = sum(1 for value in values if lower <= value <= upper)
        else:
            count = sum(1 for value in values if lower <= value < upper)
        buckets.append((lower, upper, count))
    return buckets


def count_alerts_at_threshold(
    session: Session,
    *,
    batch_id: str | None,
    scope: list[str] | None,
    threshold: float,
) -> int:
    """Count how many students a simulated threshold would flag.

    This never changes the production threshold: it only reports the volume a
    given cut-off would produce on the current batch.
    """
    filters = CohortFilters(batch_id=batch_id, scope=scope)
    row = (
        _filtered(session, filters, func.count(GoldPrediction.id))
        .filter(GoldPrediction.proba_abandon >= threshold)
        .one()
    )
    return int(row[0] or 0)


def list_audit_events(session: Session, *, limit: int = 200) -> list[AuditEvent]:
    """Return the most recent accountability records."""
    rows = (
        session.query(PrivacyAuditLog)
        .order_by(PrivacyAuditLog.created_at.desc(), PrivacyAuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        AuditEvent(
            action=str(row.action),
            actor=str(row.actor),
            target_type=str(row.target_type),
            target_id=row.target_id,
            reason=str(row.reason),
            created_at=row.created_at,
        )
        for row in rows
    ]


def latest_drift(session: Session) -> DriftSummary | None:
    """Return the latest persisted drift report summary."""
    row = (
        session.query(GoldDriftReport)
        .order_by(GoldDriftReport.created_at.desc(), GoldDriftReport.id.desc())
        .first()
    )
    if row is None:
        return None
    return DriftSummary(
        status=str(row.status),
        watch_count=int(row.watch_count),
        alert_count=int(row.alert_count),
        created_at=row.created_at,
    )


def audit_action_counts(session: Session) -> list[tuple[str, int]]:
    """Return audit event counts per action, most frequent first."""
    rows = (
        session.query(PrivacyAuditLog.action, func.count(PrivacyAuditLog.id))
        .group_by(PrivacyAuditLog.action)
        .all()
    )
    return sorted(((str(action), int(count)) for action, count in rows), key=lambda x: -x[1])
