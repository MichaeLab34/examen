"""Reusable training workflow for the dropout-risk model.

The certification notebook remains the narrative artifact. This module carries
the operational training path used by the CLI/CI: deterministic preparation,
train/validation/test separation, threshold selection on validation data, then
final reporting on an untouched test set.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import features as F
from .preprocessing import clean_raw
from .serving import ModelBundle, save_bundle


@dataclass(frozen=True)
class TrainingResult:
    """Artifacts and metrics produced by a training run."""

    bundle: ModelBundle
    metrics: dict[str, Any]
    output_path: Path | None = None


def split_train_validation_test_indices(
    y: pd.Series,
    *,
    random_state: int = 42,
    allow_fallback: bool = False,
) -> tuple[pd.Index, pd.Index, pd.Index]:
    """Return train, validation and test indices with the project split policy."""
    class_counts = y.value_counts(dropna=False)
    can_stratify = len(y) >= 5 and len(class_counts) > 1 and class_counts.min() >= 2
    stratify = y if can_stratify else None

    try:
        train_val_idx, test_idx = train_test_split(
            y.index,
            test_size=0.2,
            random_state=random_state,
            stratify=stratify,
        )
        y_train_val = y.loc[train_val_idx]
        val_stratify = (
            y_train_val if can_stratify and y_train_val.value_counts().min() >= 2 else None
        )
        train_idx, val_idx = train_test_split(
            train_val_idx,
            test_size=0.25,
            random_state=random_state,
            stratify=val_stratify,
        )
    except ValueError:
        if not allow_fallback:
            raise
        ordered = list(y.index)
        n_test = max(1, round(len(ordered) * 0.2)) if len(ordered) > 1 else 0
        n_val = max(1, round((len(ordered) - n_test) * 0.25)) if len(ordered) > 2 else 0
        test_idx = ordered[-n_test:] if n_test else []
        val_idx = ordered[-n_test - n_val : -n_test] if n_val else []
        train_idx = [idx for idx in ordered if idx not in set(test_idx) | set(val_idx)]

    return pd.Index(train_idx), pd.Index(val_idx), pd.Index(test_idx)


def assign_split_labels(
    y: pd.Series,
    *,
    random_state: int = 42,
    allow_fallback: bool = False,
) -> pd.Series:
    """Label rows as train, validation or test using the canonical split policy."""
    train_idx, val_idx, test_idx = split_train_validation_test_indices(
        y,
        random_state=random_state,
        allow_fallback=allow_fallback,
    )
    labels = pd.Series("train", index=y.index, dtype="object")
    labels.loc[val_idx] = "validation"
    labels.loc[test_idx] = "test"
    return labels


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    """Build the preprocessing pipeline for tabular scoring features."""
    numeric_cols = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_cols = [col for col in X.columns if col not in numeric_cols]

    return ColumnTransformer(
        [
            (
                "num",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_cols,
            ),
            (
                "cat",
                Pipeline(
                    [
                        ("imp", SimpleImputer(strategy="most_frequent")),
                        ("oh", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_cols,
            ),
        ]
    )


def select_threshold_by_cost(
    y_true: pd.Series | np.ndarray,
    proba: np.ndarray,
    *,
    cost_fn: float = 5.0,
    cost_fp: float = 1.0,
    thresholds: np.ndarray | None = None,
) -> tuple[float, dict[str, float]]:
    """Select the threshold that minimizes business cost on validation data."""
    if thresholds is None:
        thresholds = np.linspace(0.05, 0.95, 181)

    best_threshold = float(thresholds[0])
    best_cost = float("inf")
    best_stats: dict[str, float] = {}

    for threshold in thresholds:
        pred = (proba >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
        cost = cost_fn * fn + cost_fp * fp
        if cost < best_cost:
            best_cost = float(cost)
            best_threshold = float(threshold)
            best_stats = {
                "cost": float(cost),
                "tn": float(tn),
                "fp": float(fp),
                "fn": float(fn),
                "tp": float(tp),
                "recall": float(tp / (tp + fn)) if (tp + fn) else 0.0,
                "precision": float(tp / (tp + fp)) if (tp + fp) else 0.0,
            }

    return best_threshold, best_stats


def prepare_training_frame(raw_df: pd.DataFrame, catalogue: pd.DataFrame) -> pd.DataFrame:
    """Clean, enrich and engineer features from raw student data."""
    df = clean_raw(raw_df)
    df = F.enrich_with_catalogue(df, catalogue)
    return F.add_engineered_features(df)


def train_model(
    raw_df: pd.DataFrame,
    catalogue: pd.DataFrame,
    *,
    output_path: str | Path | None = None,
    random_state: int = 42,
    cost_fn: float = 5.0,
    cost_fp: float = 1.0,
) -> TrainingResult:
    """Train and optionally persist a `ModelBundle`.

    Splits:
    - 20% final test, never used for hyperparameter or threshold selection.
    - 20% of remaining training data as validation for threshold selection.
    """
    df = prepare_training_frame(raw_df, catalogue)
    feature_cols = F.scoring_feature_columns(df)
    F.assert_no_leakage(feature_cols)

    X = df[feature_cols]
    y = df[F.TARGET_CLF].astype(int)

    train_idx, val_idx, test_idx = split_train_validation_test_indices(
        y,
        random_state=random_state,
    )
    X_train, y_train = X.loc[train_idx], y.loc[train_idx]
    X_val, y_val = X.loc[val_idx], y.loc[val_idx]
    X_test, y_test = X.loc[test_idx], y.loc[test_idx]

    pipeline = Pipeline(
        [
            ("pre", build_preprocessor(X_train)),
            ("clf", LogisticRegression(max_iter=3000, class_weight="balanced")),
        ]
    )
    grid = {"clf__C": [0.02, 0.05, 0.1, 0.5, 1.0, 2.0]}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_state)
    search = GridSearchCV(pipeline, grid, scoring="roc_auc", cv=cv, n_jobs=1)
    search.fit(X_train, y_train)

    final_model = search.best_estimator_
    proba_val = final_model.predict_proba(X_val)[:, 1]
    threshold, threshold_stats = select_threshold_by_cost(
        y_val,
        proba_val,
        cost_fn=cost_fn,
        cost_fp=cost_fp,
    )

    proba_test = final_model.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= threshold).astype(int)
    metrics: dict[str, Any] = {
        "auc_cv": float(search.best_score_),
        "auc_test": float(roc_auc_score(y_test, proba_test)),
        "average_precision_test": float(average_precision_score(y_test, proba_test)),
        "recall_test": float(recall_score(y_test, pred_test)),
        "precision_test": float(precision_score(y_test, pred_test, zero_division=0)),
        "f1_test": float(f1_score(y_test, pred_test)),
        "threshold": threshold,
        "threshold_selection": "validation_cost_minimization",
        "threshold_validation_stats": threshold_stats,
        "best_params": search.best_params_,
        "cost_fn_fp": [cost_fn, cost_fp],
        "n_train": int(len(X_train)),
        "n_validation": int(len(X_val)),
        "n_test": int(len(X_test)),
        "n_features": int(len(feature_cols)),
    }

    bundle = ModelBundle(
        pipeline=final_model,
        feature_cols=feature_cols,
        threshold=threshold,
        catalogue=catalogue,
        metadata=metrics,
    )

    saved_path: Path | None = None
    if output_path is not None:
        saved_path = save_bundle(bundle, output_path)

    return TrainingResult(bundle=bundle, metrics=metrics, output_path=saved_path)
