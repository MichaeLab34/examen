"""Run policies for retraining and human-approved model promotion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Mapping


@dataclass(frozen=True)
class RetrainingDecision:
    """Operational decision produced from drift, calendar and label availability."""

    action: str
    should_train_candidate: bool
    requires_human_review: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PromotionDecision:
    """Result of the technical gate and the mandatory human approval."""

    eligible_for_review: bool
    approved_for_production: bool
    human_approval_required: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_retraining(
    drift_report: Mapping[str, Any],
    *,
    trained_on: date,
    as_of: date,
    labels_available: bool,
    performance_alert: bool = False,
    annual_interval_days: int = 365,
) -> RetrainingDecision:
    """Choose the next Run action for the university cohort cycle.

    Drift can trigger an investigation immediately, but a supervised model must
    not be retrained without fresh dropout labels. The calendar is therefore an
    annual safety net rather than the monthly cadence used for industrial sensors.
    """

    drift_status = str(drift_report.get("summary", {}).get("status", "missing"))
    drift_alert = drift_status == "alert"
    calendar_due = (as_of - trained_on).days >= annual_interval_days

    triggers: list[str] = []
    if drift_alert:
        triggers.append("data_drift_alert")
    if performance_alert:
        triggers.append("performance_alert")
    if calendar_due:
        triggers.append("annual_review_due")

    if not triggers:
        return RetrainingDecision(
            action="monitor",
            should_train_candidate=False,
            requires_human_review=False,
            reasons=("no_trigger",),
        )

    if not labels_available:
        return RetrainingDecision(
            action="investigate_and_collect_labels",
            should_train_candidate=False,
            requires_human_review=True,
            reasons=tuple(triggers + ["fresh_labels_unavailable"]),
        )

    return RetrainingDecision(
        action="train_candidate",
        should_train_candidate=True,
        requires_human_review=True,
        reasons=tuple(triggers),
    )


def evaluate_candidate_promotion(
    candidate_metrics: Mapping[str, Any],
    *,
    production_metrics: Mapping[str, Any] | None = None,
    human_approved: bool = False,
    min_auc: float = 0.85,
    min_recall: float = 0.90,
    max_fairness_gap: float = 0.10,
) -> PromotionDecision:
    """Apply the student-risk promotion gate before moving the production alias."""

    reasons: list[str] = []
    required = ("auc_test", "recall_test", "fairness_recall_gap_test")
    missing = [key for key in required if key not in candidate_metrics]
    if missing:
        reasons.append(f"missing_metrics:{','.join(missing)}")
    else:
        auc = float(candidate_metrics["auc_test"])
        recall = float(candidate_metrics["recall_test"])
        fairness_gap = float(candidate_metrics["fairness_recall_gap_test"])
        if auc < min_auc:
            reasons.append(f"auc_below_{min_auc:.2f}")
        if recall < min_recall:
            reasons.append(f"recall_below_{min_recall:.2f}")
        if fairness_gap > max_fairness_gap:
            reasons.append(f"fairness_gap_above_{max_fairness_gap:.2f}")
        if production_metrics is not None and "recall_test" in production_metrics:
            production_recall = float(production_metrics["recall_test"])
            if recall < production_recall:
                reasons.append("recall_regression_vs_production")

    eligible = not reasons
    if eligible and not human_approved:
        reasons.append("human_approval_required")

    return PromotionDecision(
        eligible_for_review=eligible,
        approved_for_production=eligible and human_approved,
        human_approval_required=True,
        reasons=tuple(reasons),
    )
