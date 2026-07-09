"""Monitoring helpers for data drift reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def _distribution(values: pd.Series, bins: np.ndarray) -> np.ndarray:
    counts, _ = np.histogram(values.dropna().astype(float), bins=bins)
    total = counts.sum()
    if total == 0:
        return np.full(len(counts), 1.0 / len(counts))
    return counts / total


def population_stability_index(
    reference: pd.Series,
    current: pd.Series,
    *,
    bins: int = 10,
    epsilon: float = 1e-6,
) -> float:
    """Compute PSI between a reference and current numeric distribution."""
    ref = pd.to_numeric(reference, errors="coerce").dropna()
    cur = pd.to_numeric(current, errors="coerce").dropna()
    if ref.empty or cur.empty:
        return float("nan")

    quantiles = np.linspace(0, 1, bins + 1)
    edges = np.unique(np.quantile(ref, quantiles))
    if len(edges) < 3:
        min_value = min(ref.min(), cur.min())
        max_value = max(ref.max(), cur.max())
        if min_value == max_value:
            return 0.0
        edges = np.linspace(min_value, max_value, bins + 1)

    edges[0] = min(edges[0], cur.min()) - epsilon
    edges[-1] = max(edges[-1], cur.max()) + epsilon
    ref_dist = np.clip(_distribution(ref, edges), epsilon, None)
    cur_dist = np.clip(_distribution(cur, edges), epsilon, None)
    return float(np.sum((cur_dist - ref_dist) * np.log(cur_dist / ref_dist)))


def classify_psi(psi: float, *, watch_threshold: float = 0.1, alert_threshold: float = 0.25) -> str:
    """Classify PSI according to common monitoring thresholds."""
    if np.isnan(psi):
        return "missing"
    if psi >= alert_threshold:
        return "alert"
    if psi >= watch_threshold:
        return "watch"
    return "ok"


def build_drift_report(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    *,
    feature_cols: list[str] | None = None,
    watch_threshold: float = 0.1,
    alert_threshold: float = 0.25,
) -> dict[str, Any]:
    """Build a compact PSI drift report for numeric columns."""
    if feature_cols is None:
        common_cols = [col for col in reference_df.columns if col in current_df.columns]
        feature_cols = [
            col
            for col in common_cols
            if pd.api.types.is_numeric_dtype(reference_df[col])
            or pd.api.types.is_numeric_dtype(current_df[col])
        ]

    features = []
    for col in feature_cols:
        if col not in reference_df.columns or col not in current_df.columns:
            features.append({"feature": col, "psi": None, "status": "missing"})
            continue
        psi = population_stability_index(reference_df[col], current_df[col])
        features.append(
            {
                "feature": col,
                "psi": None if np.isnan(psi) else round(psi, 6),
                "status": classify_psi(
                    psi,
                    watch_threshold=watch_threshold,
                    alert_threshold=alert_threshold,
                ),
            }
        )

    alert_count = sum(1 for item in features if item["status"] == "alert")
    watch_count = sum(1 for item in features if item["status"] == "watch")
    return {
        "summary": {
            "reference_rows": int(len(reference_df)),
            "current_rows": int(len(current_df)),
            "features_checked": int(len(features)),
            "watch_count": int(watch_count),
            "alert_count": int(alert_count),
            "status": "alert" if alert_count else "watch" if watch_count else "ok",
            "watch_threshold": watch_threshold,
            "alert_threshold": alert_threshold,
        },
        "features": features,
    }


def write_drift_report(report: dict[str, Any], path: str | Path) -> Path:
    """Write a drift report as pretty JSON."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return output
