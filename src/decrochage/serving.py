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


# --- Explicabilité locale (restitution aux référents) ------------------------
#
# Le modèle retenu est une régression logistique : la contribution d'une
# variable au log-odds est **exactement** `coefficient x valeur transformée`.
# Aucune approximation par échantillonnage (SHAP) n'est donc nécessaire à
# l'exécution — c'est la conséquence directe du choix d'un modèle linéaire.
#
# Attention : ces contributions s'additionnent sur l'échelle du log-odds, pas
# en probabilité. Elles indiquent un ordre d'importance et un sens, jamais une
# part de responsabilité.

_NEGLIGIBLE_CONTRIBUTION = 1e-12


@dataclass(frozen=True)
class FeatureContribution:
    """Signed contribution of one transformed feature to the log-odds.

    Two values are carried on purpose and must not be confused:

    - `transformed_value` is what the model actually multiplied by its
      coefficient (imputed, standardized or one-hot encoded). It is the only
      value for which `coefficient * value` is meaningful.
    - `raw_value` is the value the student record actually holds, resolved back
      to `source_column`. **This is the only one a human may be shown**: a
      standardized -1.8 displayed as a completion rate would read "-180 %".
    """

    name: str
    contribution: float
    transformed_value: float
    source_column: str | None = None
    raw_value: Any = None

    @property
    def increases_risk(self) -> bool:
        return self.contribution > 0

    @property
    def direction(self) -> str:
        return "aggravant" if self.increases_risk else "protecteur"


@dataclass(frozen=True)
class PredictionExplanation:
    """Additive decomposition of a single prediction.

    Invariant: `intercept + sum(c.contribution for c in contributions)` equals
    the model log-odds, which is what `test_explain.py` asserts.
    """

    intercept: float
    log_odds: float
    proba: float
    contributions: list[FeatureContribution]
    top_n: int = 5

    def _material(self) -> list[FeatureContribution]:
        return [
            item for item in self.contributions if abs(item.contribution) > _NEGLIGIBLE_CONTRIBUTION
        ]

    def risk_factors(self, top_n: int | None = None) -> list[FeatureContribution]:
        """Return the strongest risk-increasing contributions."""
        limit = self.top_n if top_n is None else top_n
        return [item for item in self._material() if item.increases_risk][:limit]

    def protective_factors(self, top_n: int | None = None) -> list[FeatureContribution]:
        """Return the strongest risk-decreasing contributions."""
        limit = self.top_n if top_n is None else top_n
        return [item for item in self._material() if not item.increases_risk][:limit]


_TRANSFORMER_PREFIXES = ("num__", "cat__", "remainder__")


def resolve_source_column(transformed_name: str, columns: list[str]) -> str | None:
    """Map a transformed feature name back to the Gold column it came from.

    `num__taux_rendu_devoirs` -> `taux_rendu_devoirs`
    `cat__mention_bac_TB`     -> `mention_bac`   (longest matching column wins)

    Returning the source column is what allows a risk sheet to display the value
    the record actually holds instead of its standardized counterpart.
    """
    base = str(transformed_name)
    for prefix in _TRANSFORMER_PREFIXES:
        if base.startswith(prefix):
            base = base[len(prefix) :]
            break
    if base in columns:
        return base
    candidates = [column for column in columns if base.startswith(f"{column}_")]
    return max(candidates, key=len) if candidates else None


def can_explain(bundle: ModelBundle) -> bool:
    """Return True when the bundle exposes a linear model we can decompose."""
    pipeline = getattr(bundle, "pipeline", None)
    steps = getattr(pipeline, "named_steps", None)
    if not steps or "pre" not in steps or "clf" not in steps:
        return False
    return hasattr(steps["clf"], "coef_") and hasattr(steps["pre"], "get_feature_names_out")


def explain_prediction(
    bundle: ModelBundle,
    gold_features: pd.DataFrame,
    *,
    row: int = 0,
    top_n: int = 5,
) -> PredictionExplanation:
    """Decompose one prediction into additive per-feature contributions.

    Raises:
        ValueError: when the bundle does not carry a linear `pre`/`clf` pipeline,
            or when `row` is out of range.
    """
    if not can_explain(bundle):
        raise ValueError("This bundle does not expose a linear pre/clf pipeline")
    if gold_features.empty:
        raise ValueError("gold_features must contain at least one row")
    if not 0 <= row < len(gold_features):
        raise ValueError(f"row {row} is out of range for {len(gold_features)} records")

    steps = bundle.pipeline.named_steps
    preprocessor = steps["pre"]
    classifier = steps["clf"]

    X = gold_features.reindex(columns=bundle.feature_cols).iloc[[row]]
    transformed = preprocessor.transform(X)
    if hasattr(transformed, "toarray"):  # OneHotEncoder returns a sparse matrix
        transformed = transformed.toarray()
    values = np.asarray(transformed, dtype=float).ravel()

    names = [str(name) for name in preprocessor.get_feature_names_out()]
    coefficients = np.asarray(classifier.coef_, dtype=float).ravel()
    if not len(names) == len(coefficients) == len(values):
        raise ValueError("Inconsistent transformed feature count for this bundle")

    products = coefficients * values
    intercept = float(np.asarray(classifier.intercept_, dtype=float).ravel()[0])
    log_odds = intercept + float(products.sum())

    source_row = X.iloc[0]
    contributions = []
    for name, product, value in zip(names, products, values):
        column = resolve_source_column(name, list(X.columns))
        contributions.append(
            FeatureContribution(
                name=name,
                contribution=float(product),
                transformed_value=float(value),
                source_column=column,
                raw_value=(None if column is None else source_row.get(column)),
            )
        )
    contributions.sort(key=lambda item: abs(item.contribution), reverse=True)

    return PredictionExplanation(
        intercept=intercept,
        log_odds=log_odds,
        proba=float(1.0 / (1.0 + np.exp(-log_odds))),
        contributions=contributions,
        top_n=top_n,
    )
