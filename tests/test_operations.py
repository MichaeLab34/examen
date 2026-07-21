from datetime import date

from decrochage.operations import decide_retraining, evaluate_candidate_promotion


def test_drift_without_fresh_labels_triggers_investigation_not_training() -> None:
    report = {"summary": {"status": "alert"}}

    decision = decide_retraining(
        report,
        trained_on=date(2025, 9, 1),
        as_of=date(2026, 2, 1),
        labels_available=False,
    )

    assert decision.action == "investigate_and_collect_labels"
    assert decision.should_train_candidate is False
    assert "fresh_labels_unavailable" in decision.reasons


def test_annual_review_with_labels_trains_candidate() -> None:
    decision = decide_retraining(
        {"summary": {"status": "ok"}},
        trained_on=date(2025, 7, 1),
        as_of=date(2026, 7, 2),
        labels_available=True,
    )

    assert decision.action == "train_candidate"
    assert decision.should_train_candidate is True
    assert decision.requires_human_review is True


def test_promotion_requires_non_regression_fairness_and_human_approval() -> None:
    candidate = {
        "auc_test": 0.95,
        "recall_test": 0.96,
        "fairness_recall_gap_test": 0.04,
    }
    production = {"recall_test": 0.95}

    waiting = evaluate_candidate_promotion(candidate, production_metrics=production)
    approved = evaluate_candidate_promotion(
        candidate,
        production_metrics=production,
        human_approved=True,
    )

    assert waiting.eligible_for_review is True
    assert waiting.approved_for_production is False
    assert approved.approved_for_production is True


def test_promotion_rejects_recall_regression() -> None:
    decision = evaluate_candidate_promotion(
        {
            "auc_test": 0.95,
            "recall_test": 0.92,
            "fairness_recall_gap_test": 0.04,
        },
        production_metrics={"recall_test": 0.96},
        human_approved=True,
    )

    assert decision.approved_for_production is False
    assert "recall_regression_vs_production" in decision.reasons
