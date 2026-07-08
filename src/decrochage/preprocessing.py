"""Nettoyage des données brutes « décrochage étudiant ».

Le jeu de données est volontairement imparfait (cf. énoncé) : doublons exacts,
nombres stockés en texte (virgules décimales FR, symbole « % », unité « km »),
encodages catégoriels incohérents (casse/espaces/synonymes), dates en formats
multiples, valeurs manquantes.

Toutes les conversions sont regroupées ici pour être reproductibles et
appliquées **à l'identique** en entraînement et en production (via `serving`).
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Parsing des numériques stockés en texte
# --------------------------------------------------------------------------- #

_NUM_CLEAN_RE = re.compile(r"[%\s]|km", flags=re.IGNORECASE)


def parse_number_fr(value) -> float:
    """Convertit une valeur texte « à la française » en float.

    Gère : virgule décimale (« 61,8 »), symbole pourcent (« 61.4% », « 85,0 »),
    unité « km » (« 14.4 km »), espaces. Retourne NaN si non convertible.
    """
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return np.nan
    s = _NUM_CLEAN_RE.sub("", s)     # retire %, espaces, « km »
    s = s.replace(",", ".")          # virgule décimale FR → point
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_numeric_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = df[col].map(parse_number_fr)
    return df


# --------------------------------------------------------------------------- #
# Parsing des dates multi-formats
# --------------------------------------------------------------------------- #

# Formats explicites rencontrés : AAAA-MM-JJ, JJ/MM/AAAA, « 02 Sep 2024 »
_FR_MONTHS = {
    "jan": "01", "fev": "02", "feb": "02", "mar": "03", "avr": "04", "apr": "04",
    "mai": "05", "may": "05", "jun": "06", "jui": "07", "jul": "07", "aou": "08",
    "aug": "08", "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


def parse_date_multi(value) -> pd.Timestamp:
    """Parse une date en essayant plusieurs formats ; NaT si échec."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return pd.NaT
    s = str(value).strip()
    if s == "":
        return pd.NaT
    # pandas gère la majorité (ISO, JJ/MM/AAAA avec dayfirst, « 02 Sep 2024 »)
    for dayfirst in (False, True):
        dt = pd.to_datetime(s, dayfirst=dayfirst, errors="coerce")
        if pd.notna(dt):
            return dt
    return pd.NaT


# --------------------------------------------------------------------------- #
# Normalisation des catégorielles
# --------------------------------------------------------------------------- #

def _strip_lower(s) -> str:
    return str(s).strip().lower()


_SEXE_MAP = {
    "f": "F", "femme": "F", "femelle": "F",
    "m": "M", "h": "M", "homme": "M",
    "autre": "Autre", "other": "Autre", "nb": "Autre",
}

_BAC_MAP = {
    "general": "general", "generale": "general", "général": "general",
    "générale": "general", "gen": "general", "g": "general",
    "techno": "techno", "technologique": "techno", "techn": "techno", "t": "techno",
    "pro": "pro", "professionnel": "pro", "professionnelle": "pro", "p": "pro",
}

_MENTION_MAP = {
    "passable": "passable", "p": "passable", "sans mention": "passable",
    "ab": "AB", "assez bien": "AB",
    "b": "B", "bien": "B",
    "tb": "TB", "tres bien": "TB", "très bien": "TB",
}

_BOURSIER_MAP = {
    "oui": 1, "o": 1, "yes": 1, "y": 1, "1": 1, "true": 1, "vrai": 1,
    "non": 0, "n": 0, "no": 0, "0": 0, "false": 0, "faux": 0,
}


def normalize_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Harmonise les encodages catégoriels incohérents."""
    df = df.copy()

    if "filiere" in df.columns:
        # Casse/espaces : « biologie », « STAPS », « Gestion » → Titre normalisé
        df["filiere"] = df["filiere"].astype(str).str.strip().str.title()

    if "sexe" in df.columns:
        df["sexe"] = df["sexe"].map(lambda x: _SEXE_MAP.get(_strip_lower(x), np.nan))

    if "bac_type" in df.columns:
        df["bac_type"] = df["bac_type"].map(lambda x: _BAC_MAP.get(_strip_lower(x), np.nan))

    if "mention_bac" in df.columns:
        df["mention_bac"] = df["mention_bac"].map(lambda x: _MENTION_MAP.get(_strip_lower(x), np.nan))

    if "boursier" in df.columns:
        df["boursier"] = df["boursier"].map(lambda x: _BOURSIER_MAP.get(_strip_lower(x), np.nan))

    if "etablissement_origine" in df.columns:
        df["etablissement_origine"] = (
            df["etablissement_origine"].astype(str).str.strip().str.lower()
            .replace({"nan": np.nan, "": np.nan})
        )

    return df


# --------------------------------------------------------------------------- #
# Pipeline de nettoyage complet (hors imputation / encodage ML)
# --------------------------------------------------------------------------- #

# Colonnes numériques susceptibles d'être stockées en texte
TEXT_NUMERIC_COLS = ["distance_domicile_km", "taux_presence_pct"]


def clean_raw(df: pd.DataFrame, *, drop_duplicates: bool = True) -> pd.DataFrame:
    """Applique tout le nettoyage déterministe sur un DataFrame brut.

    Étapes : dédoublonnage exact → parsing numériques texte → parsing date →
    normalisation catégorielles. N'impute PAS et n'encode PAS (fait dans la
    Pipeline sklearn, fit sur le train uniquement, pour éviter toute fuite).
    """
    df = df.copy()

    if drop_duplicates:
        df = df.drop_duplicates().reset_index(drop=True)

    df = parse_numeric_columns(df, TEXT_NUMERIC_COLS)

    if "date_inscription" in df.columns:
        df["date_inscription_parsed"] = df["date_inscription"].map(parse_date_multi)

    df = normalize_categoricals(df)

    return df
