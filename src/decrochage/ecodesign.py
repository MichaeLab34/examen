"""Éco-conception : mesurer le coût de calcul d'un entraînement et le rapporter au gain.

Le contexte du projet (une université, ~5 200 étudiants par an, un scoring par semestre)
rend l'empreinte d'un entraînement modeste dans l'absolu. L'enjeu n'est donc pas la
mesure métrologique mais l'**arbitrage** : accepte-t-on de multiplier le coût de calcul
pour un gain de performance qui n'est pas significatif ?

`CodeCarbon` estime l'énergie (kWh) et l'empreinte (gCO₂eq) à partir du matériel et du
**mix électrique** du pays (`country_iso_code="FRA"` : mix français bas carbone).

⚠️ Limites assumées et à annoncer :
- sous Windows, l'interface RAPL (puissance CPU) est indisponible → l'estimation CPU est
  approximative, souvent sous-estimée ;
- la mesure dépend de la machine et de sa charge : elle sert à **comparer des modèles
  entre eux dans une même session**, pas à publier une empreinte absolue.

Si CodeCarbon est absent ou échoue, le suivi se dégrade proprement : la durée reste
mesurée (`time.perf_counter`) et les colonnes énergie/CO₂ valent `None`.
"""

from __future__ import annotations

import time
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

FRANCE_ISO_CODE = "FRA"


@contextmanager
def track_emissions(label: str, output_dir: Path | None = None) -> Iterator[dict[str, Any]]:
    """Mesure la durée, l'énergie et le CO₂ d'un bloc de calcul.

    À la sortie du bloc, le dictionnaire cédé contient `label`, `duree_s`, `energie_kwh`
    et `emissions_kg` (ces deux dernières à `None` si CodeCarbon est indisponible).
    L'appelant peut y ajouter ses propres clés (métrique de performance, par exemple).
    """
    holder: dict[str, Any] = {
        "label": label,
        "duree_s": None,
        "energie_kwh": None,
        "emissions_kg": None,
        "mesure_indisponible": None,
    }
    tracker = _start_tracker(label, output_dir, holder)
    start = time.perf_counter()
    try:
        yield holder
    finally:
        holder["duree_s"] = time.perf_counter() - start
        if tracker is not None:
            _stop_tracker(tracker, holder, label)


def _start_tracker(label: str, output_dir: Path | None, holder: dict[str, Any]) -> Any | None:
    try:
        from codecarbon import OfflineEmissionsTracker
    except Exception as exc:  # noqa: BLE001 — instrumentation optionnelle
        holder["mesure_indisponible"] = f"import CodeCarbon : {type(exc).__name__}: {exc}"
        warnings.warn(
            f"CodeCarbon indisponible ({exc}) — seule la durée sera mesurée pour '{label}'.",
            RuntimeWarning,
            stacklevel=3,
        )
        return None

    try:
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)
        # output_methods remplace save_to_file depuis CodeCarbon 3 ; sans dossier de
        # sortie, on ne persiste rien (cas des tests unitaires).
        tracker = OfflineEmissionsTracker(
            country_iso_code=FRANCE_ISO_CODE,
            output_dir=str(output_dir) if output_dir is not None else ".",
            output_file="emissions.csv",
            measure_power_secs=5,
            tracking_mode="process",
            log_level="error",
            output_methods=["csv"] if output_dir is not None else [],
            allow_multiple_runs=True,
        )
        tracker.start()
        return tracker
    except Exception as exc:  # noqa: BLE001 — ne jamais interrompre un entraînement
        holder["mesure_indisponible"] = f"démarrage : {type(exc).__name__}: {exc}"
        warnings.warn(
            f"Démarrage CodeCarbon en échec ({exc}) pour '{label}'.",
            RuntimeWarning,
            stacklevel=3,
        )
        return None


def _stop_tracker(tracker: Any, holder: dict[str, Any], label: str) -> None:
    try:
        emissions = tracker.stop()
        holder["emissions_kg"] = None if emissions is None else float(emissions)
        data = tracker.final_emissions_data
        energy = getattr(data, "energy_consumed", None)
        holder["energie_kwh"] = None if energy is None else float(energy)
    except Exception as exc:  # noqa: BLE001 — arrêt du tracker non critique
        holder["mesure_indisponible"] = f"arrêt : {type(exc).__name__}: {exc}"
        warnings.warn(
            f"Arrêt CodeCarbon en échec ({exc}) pour '{label}'.",
            RuntimeWarning,
            stacklevel=3,
        )


def summarize_runs(runs: list[dict[str, Any]], *, metric_key: str = "auc") -> pd.DataFrame:
    """Construit le tableau `modèle → durée, énergie, gCO₂eq, métrique`."""
    records = []
    for run in runs:
        emissions_kg = run.get("emissions_kg")
        records.append(
            {
                "Modèle": run.get("label"),
                "Durée entraînement (s)": run.get("duree_s"),
                "Énergie (kWh)": run.get("energie_kwh"),
                "gCO2eq": None if emissions_kg is None else float(emissions_kg) * 1000.0,
                metric_key: run.get(metric_key),
            }
        )
    return pd.DataFrame.from_records(records)


def cost_per_metric_point(
    candidate_metric: float,
    reference_metric: float,
    candidate_cost: float,
    reference_cost: float,
) -> float:
    """Coût supplémentaire consenti par point de métrique gagné face à une référence.

    Renvoie `inf` quand le candidat ne gagne rien : dépenser plus de calcul sans gagner
    de performance n'a pas de contrepartie, et c'est précisément le cas à documenter.
    """
    gain = candidate_metric - reference_metric
    surcout = candidate_cost - reference_cost
    if gain <= 0:
        return float("inf")
    return surcout / gain


def build_arbitrage_table(
    summary: pd.DataFrame,
    *,
    reference_model: str,
    metric_key: str = "auc",
    cost_key: str = "Durée entraînement (s)",
) -> pd.DataFrame:
    """Ajoute au tableau le surcoût et le coût par point de métrique face au modèle retenu."""
    if reference_model not in set(summary["Modèle"]):
        raise ValueError(f"Modèle de référence absent du tableau : {reference_model!r}")

    reference = summary.loc[summary["Modèle"] == reference_model].iloc[0]
    ref_metric = float(reference[metric_key])
    ref_cost = float(reference[cost_key])

    table = summary.copy()
    table["Surcoût calcul (x)"] = table[cost_key].astype(float) / ref_cost
    table[f"Gain {metric_key}"] = table[metric_key].astype(float) - ref_metric
    table[f"Coût / point {metric_key}"] = [
        cost_per_metric_point(float(m), ref_metric, float(c), ref_cost)
        for m, c in zip(table[metric_key], table[cost_key], strict=True)
    ]
    return table
