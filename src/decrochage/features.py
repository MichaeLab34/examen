"""Périmètre de scoring et feature engineering.

Ce module centralise **les décisions méthodologiques structurantes** du cas
d'usage, de sorte qu'elles soient testables et impossibles à contourner par
inadvertance dans le notebook.

Trois catégories de colonnes sont écartées des variables explicatives :

1. `LEAKAGE_TARGET_COLS` — fuite de données : la cible secondaire
   `moyenne_finale` (résultat de fin de semestre, structurellement corrélé au
   décrochage) ne doit jamais servir à prédire `abandon`.
2. `LEAKAGE_TEMPORAL_COLS` — fuite temporelle : `moyenne_partiels_s1` et
   `nb_ue_validees_s1` sont consolidées en fin de S1, donc indisponibles au
   moment du scoring à mi-S1.
3. `ID_COLS` — identifiants sans pouvoir prédictif (et risque de sur-apprentissage).
4. `LEURRE_COLS` — leurres explicitement annoncés dans l'énoncé, sans pouvoir
   prédictif ; conservés pour être discutés puis exclus.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# --- Cibles ---
TARGET_CLF = "abandon"  # cible principale : classification binaire (0/1)
TARGET_REG = "moyenne_finale"  # cible secondaire : régression (/20)

# --- Colonnes à exclure du périmètre de scoring (classification `abandon`) ---
ID_COLS = ["student_id", "id_dossier"]
CONSTANT_COLS = [
    "annee_universitaire",
    "niveau",
]  # constantes (2024-2025 ; L1) → aucune information
LEURRE_COLS = ["groupe_td", "couleur_carte_etudiante", "jour_inscription"]
LEAKAGE_TARGET_COLS = ["moyenne_finale"]  # fuite de données
LEAKAGE_TEMPORAL_COLS = ["moyenne_partiels_s1", "nb_ue_validees_s1"]  # fuite temporelle

# Dates brutes : non utilisables telles quelles (texte / Timestamp) ; on en dérive
# une feature numérique (`jours_inscription`) dans add_engineered_features.
RAW_DATE_COLS = ["date_inscription", "date_inscription_parsed"]

# Colonne texte libre : traitée à part (feature dérivée), retirée du tabulaire brut
TEXT_COL = "commentaire_tuteur"


def enrich_with_catalogue(df: pd.DataFrame, catalogue: pd.DataFrame) -> pd.DataFrame:
    """Jointure de la table de référence des formations via `filiere` (C1/C3).

    La casse de `filiere` est normalisée des deux côtés (Titre) pour garantir un
    appariement complet.
    """
    df = df.copy()
    cat = catalogue.copy()
    df["filiere"] = df["filiere"].astype(str).str.strip().str.title()
    cat["filiere"] = cat["filiere"].astype(str).str.strip().str.title()
    return df.merge(cat, on="filiere", how="left")


def scoring_feature_columns(df: pd.DataFrame) -> list[str]:
    """Retourne les colonnes utilisables comme variables explicatives à mi-S1.

    Exclut cibles, identifiants, constantes, leurres, colonnes de fuite
    (données + temporelle) et la colonne de texte libre brute.
    """
    excluded = set(
        ID_COLS
        + CONSTANT_COLS
        + LEURRE_COLS
        + LEAKAGE_TARGET_COLS
        + LEAKAGE_TEMPORAL_COLS
        + RAW_DATE_COLS
        + [TARGET_CLF, TARGET_REG, TEXT_COL]
    )
    return [c for c in df.columns if c not in excluded]


def assert_no_leakage(feature_cols: list[str]) -> None:
    """Garde-fou : lève une erreur si une colonne interdite figure dans les features."""
    forbidden = set(
        ID_COLS + LEAKAGE_TARGET_COLS + LEAKAGE_TEMPORAL_COLS + [TARGET_CLF, TARGET_REG]
    )
    intruders = forbidden & set(feature_cols)
    assert (
        not intruders
    ), f"Fuite de données : colonnes interdites présentes dans les features : {sorted(intruders)}"


def build_gold_dataset(
    prepared_df: pd.DataFrame,
    *,
    include_labels: bool = True,
) -> tuple[pd.DataFrame, list[str]]:
    """Build the ML-ready Gold dataset from a cleaned/enriched frame.

    The Gold dataset is the only tabular source that model training and notebook
    scoring should consume. It contains scoring features plus optional labels,
    and excludes direct identifiers, leakage columns, constants, raw dates,
    free text and explicit lure columns.
    """
    feature_cols = scoring_feature_columns(prepared_df)
    assert_no_leakage(feature_cols)

    columns = list(feature_cols)
    if include_labels:
        for target in (TARGET_CLF, TARGET_REG):
            if target in prepared_df.columns:
                columns.append(target)

    return prepared_df.loc[:, columns].copy(), feature_cols


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute des variables métier disponibles à mi-S1 (aucune fuite).

    - `taux_rendu_devoirs` : ratio devoirs rendus / attendus (engagement).
    - `heures_lms_par_connexion` : intensité moyenne d'une session LMS.
    - `ressources_par_connexion` : profondeur d'exploration des ressources.
    - `charge_travail_externe` : proxy socio-économique (heures de travail rémunéré).
    - `commentaire_present` : le tuteur a-t-il laissé un commentaire (signal faible).
    """
    df = df.copy()

    # Taux de rendu des devoirs (borné à [0, 1] ; robuste au dénominateur nul)
    denom = df["nb_devoirs_total"].replace(0, np.nan)
    df["taux_rendu_devoirs"] = (df["nb_devoirs_rendus"] / denom).clip(0, 1)

    # Intensité d'usage du LMS
    conn = df["connexions_lms_30j"].replace(0, np.nan)
    df["heures_lms_par_connexion"] = (df["heures_lms_total"] / conn).fillna(0)
    df["ressources_par_connexion"] = (df["ressources_consultees"] / conn).fillna(0)

    # Présence d'un commentaire tuteur (le contenu est ~49 % vide)
    if TEXT_COL in df.columns:
        df["commentaire_present"] = (
            df[TEXT_COL].notna() & (df[TEXT_COL].astype(str).str.strip() != "")
        ).astype(int)

    # Ancienneté d'inscription (précoce vs tardive) dérivée de la date parsée :
    # nombre de jours écoulés depuis la première inscription observée. Numérique,
    # utilisable par le modèle (le jour de semaine `jour_inscription` reste un leurre).
    if "date_inscription_parsed" in df.columns:
        d = pd.to_datetime(df["date_inscription_parsed"], errors="coerce")
        ref = d.min()
        df["jours_inscription"] = (d - ref).dt.days

    return df
