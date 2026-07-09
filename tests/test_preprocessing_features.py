import math

import pandas as pd
import pytest

from decrochage import features as F
from decrochage.preprocessing import clean_raw, parse_number_fr


def test_parse_number_fr_handles_percent_comma_and_km() -> None:
    assert parse_number_fr("61,8") == 61.8
    assert parse_number_fr("85%") == 85.0
    assert parse_number_fr("14.4 km") == 14.4
    assert math.isnan(parse_number_fr(""))


def test_clean_raw_normalizes_categories_and_drops_duplicates() -> None:
    raw = pd.DataFrame(
        [
            {
                "filiere": " informatique ",
                "sexe": "femme",
                "bac_type": "Général",
                "mention_bac": "Très bien",
                "boursier": "Oui",
                "etablissement_origine": " Lycee_Public ",
                "distance_domicile_km": "14,4 km",
                "taux_presence_pct": "85%",
                "date_inscription": "02 Sep 2024",
            }
        ]
    )
    raw = pd.concat([raw, raw], ignore_index=True)

    cleaned = clean_raw(raw)

    assert len(cleaned) == 1
    assert cleaned.loc[0, "filiere"] == "Informatique"
    assert cleaned.loc[0, "sexe"] == "F"
    assert cleaned.loc[0, "bac_type"] == "general"
    assert cleaned.loc[0, "mention_bac"] == "TB"
    assert cleaned.loc[0, "boursier"] == 1
    assert cleaned.loc[0, "etablissement_origine"] == "lycee_public"
    assert cleaned.loc[0, "distance_domicile_km"] == 14.4
    assert cleaned.loc[0, "taux_presence_pct"] == 85.0
    assert pd.notna(cleaned.loc[0, "date_inscription_parsed"])


def test_scoring_feature_columns_exclude_forbidden_columns() -> None:
    df = pd.DataFrame(
        columns=[
            "student_id",
            "id_dossier",
            "moyenne_finale",
            "moyenne_partiels_s1",
            "nb_ue_validees_s1",
            "abandon",
            "groupe_td",
            "taux_presence_pct",
        ]
    )

    features = F.scoring_feature_columns(df)

    assert features == ["taux_presence_pct"]
    F.assert_no_leakage(features)
    with pytest.raises(AssertionError):
        F.assert_no_leakage(["moyenne_finale"])
