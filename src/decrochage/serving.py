"""Service de prédiction (compétence C6) — contrat d'entrée/sortie explicite.

Le modèle est livré sous forme d'un *bundle* sérialisé (joblib) contenant :
- `pipeline` : Pipeline sklearn (imputation + encodage + scaling + modèle) ;
- `feature_cols` : liste ordonnée des colonnes attendues en entrée du pipeline ;
- `threshold` : seuil de décision retenu (justifié par le coût métier d'un faux
  négatif) ;
- `metadata` : version, date d'entraînement, métriques de référence.

La fonction `predict_proba_abandon` prend un DataFrame **brut** (tel qu'extrait
du SI scolarité / LMS), matérialise les features Gold attendues par le modèle,
puis renvoie une probabilité de décrochage et une décision au seuil retenu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from . import features as F
from .preprocessing import clean_raw


@dataclass
class ModelBundle:
    """Conteneur sérialisable du modèle et de son contexte de décision.

    `catalogue` embarque la table de référence des formations (8 lignes) pour que
    le bundle soit auto-suffisant : la jointure d'enrichissement est rejouée à
    l'inférence sans dépendre d'un fichier externe.
    """

    pipeline: Any
    feature_cols: list[str]
    threshold: float
    catalogue: Any = None
    metadata: dict = field(default_factory=dict)


def save_bundle(bundle: ModelBundle, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return path


def load_bundle(path: str | Path) -> ModelBundle:
    return joblib.load(Path(path))


def prepare_features(
    raw_df: pd.DataFrame, feature_cols: list[str], catalogue: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Materialize Gold scoring features from raw records.

    clean_raw (parsing/normalisation) → jointure catalogue → feature engineering
    → Gold dataset sans labels, dans l'ordre attendu par le pipeline.
    """
    df = clean_raw(raw_df, drop_duplicates=False)
    if catalogue is not None:
        df = F.enrich_with_catalogue(df, catalogue)
    df = F.add_engineered_features(df)
    gold_features, _ = F.build_gold_dataset(df, include_labels=False)
    # Colonnes manquantes éventuelles → créées vides (imputées par le pipeline)
    for col in feature_cols:
        if col not in gold_features.columns:
            gold_features[col] = np.nan
    return gold_features[feature_cols]


def predict_from_gold_dataset(bundle: ModelBundle, gold_features: pd.DataFrame) -> pd.DataFrame:
    """Contrat de sortie : une ligne par étudiant.

    Colonnes renvoyées :
    - `proba_abandon` : probabilité de décrochage (float ∈ [0, 1]) ;
    - `alerte` : 1 si `proba_abandon >= threshold`, sinon 0.
    """
    X = gold_features.reindex(columns=bundle.feature_cols)
    proba = bundle.pipeline.predict_proba(X)[:, 1]
    out = pd.DataFrame({"proba_abandon": proba})
    out["alerte"] = (out["proba_abandon"] >= bundle.threshold).astype(int)
    return out


def predict_proba_abandon(bundle: ModelBundle, raw_df: pd.DataFrame) -> pd.DataFrame:
    """Score raw records after converting them to Gold scoring features."""
    gold_features = prepare_features(raw_df, bundle.feature_cols, bundle.catalogue)
    return predict_from_gold_dataset(bundle, gold_features)
