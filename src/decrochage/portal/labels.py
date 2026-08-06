"""Business labels and display rules for model feature names.

The model works on transformed names produced by the `ColumnTransformer`
(`num__<column>`, `cat__<column>_<modality>`). A referent must never read those:
this module maps them to readable French wording.

Keys mirror the **actual dataset header** (`data/raw/*.csv`), not an idealized
naming: `bac_type`, `heures_travail_remunere_sem`, `motivation`. A test asserts
that every scoring column of the reference dataset has an explicit label, so a
drift between code and data shows up as a failure rather than as a technical
name leaking onto a risk sheet.
"""

from __future__ import annotations

FEATURE_LABELS: dict[str, str] = {
    # Engagement LMS et travail rendu
    "taux_rendu_devoirs": "taux de rendu des devoirs",
    "nb_devoirs_rendus": "devoirs rendus",
    "nb_devoirs_total": "devoirs attendus",
    "retards_rendus": "rendus en retard",
    "connexions_lms_30j": "connexions au LMS (30 jours)",
    "heures_lms_total": "heures passées sur le LMS",
    "heures_lms_par_connexion": "durée moyenne d'une session LMS",
    "ressources_consultees": "ressources pédagogiques consultées",
    "ressources_par_connexion": "ressources consultées par session",
    "messages_forum": "messages postés sur le forum",
    "taux_presence_pct": "taux de présence",
    "nb_ue_total": "unités d'enseignement suivies",
    # Ressenti déclaré
    "motivation": "motivation déclarée",
    "satisfaction": "satisfaction déclarée",
    "sentiment_appartenance": "sentiment d'appartenance",
    # Contexte étudiant
    "age": "âge",
    "sexe": "sexe",
    "boursier": "boursier",
    "distance_domicile_km": "distance domicile-campus",
    "heures_travail_remunere_sem": "heures de travail rémunéré par semaine",
    "charge_travail_externe": "charge de travail externe",
    "etablissement_origine": "établissement d'origine",
    "mention_bac": "mention au baccalauréat",
    "bac_type": "type de baccalauréat",
    # Dérivées et catalogue
    "jours_inscription": "ancienneté de l'inscription",
    "commentaire_present": "commentaire du tuteur renseigné",
    "filiere": "filière",
    "faculte": "faculté",
    "capacite": "capacité de la filière",
    "capacite_accueil": "capacité d'accueil de la filière",
    "taux_reussite_moyen": "taux de réussite moyen de la filière",
    "duree_annees": "durée de la formation",
    "cout_annuel_euros": "coût annuel de la formation",
    "selectivite": "sélectivité de la filière",
}

# Attributs protégés et proxys socio-économiques directs.
#
# Ces variables restent dans le modèle lorsque l'audit d'équité le justifie,
# mais elles ne sont **jamais restituées comme facteur de risque** sur la fiche
# d'un étudiant : présenter « sexe : F » sous un intitulé « facteur aggravant »
# exposerait l'établissement sur le terrain de la discrimination, quand bien même
# le coefficient serait statistiquement réel. Décision à confirmer par le DPO.
NON_DISPLAYABLE_FACTOR_COLS: frozenset[str] = frozenset(
    {
        "sexe",
        "boursier",
        "etablissement_origine",
        "distance_domicile_km",
        "heures_travail_remunere_sem",
        "charge_travail_externe",
    }
)

# Variables dont la valeur dépend du lot entier et ne peut donc pas être
# reconstruite à partir d'un enregistrement isolé : `jours_inscription` est
# calculée relativement à la première inscription observée dans le lot, elle
# vaudrait toujours 0 sur une ligne seule. Les afficher donnerait un facteur
# identique sur toutes les fiches.
BATCH_RELATIVE_COLS: frozenset[str] = frozenset({"jours_inscription"})

_TRANSFORMER_PREFIXES = ("num__", "cat__", "remainder__")


def _strip_prefix(name: str) -> str:
    for prefix in _TRANSFORMER_PREFIXES:
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def _prettify(raw: str) -> str:
    return raw.replace("_", " ").strip()


def humanize_feature(name: str) -> str:
    """Return a readable French label for a transformed feature name.

    One-hot features keep their modality: `cat__mention_bac_TB` becomes
    "mention au baccalauréat : TB".
    """
    base = _strip_prefix(str(name))
    if base in FEATURE_LABELS:
        return FEATURE_LABELS[base]

    candidates = [column for column in FEATURE_LABELS if base.startswith(f"{column}_")]
    if candidates:
        column = max(candidates, key=len)
        modality = base[len(column) + 1 :]
        return f"{FEATURE_LABELS[column]} : {_prettify(modality)}"

    return _prettify(base)


def is_displayable_factor(source_column: str | None) -> bool:
    """Return False for protected attributes and batch-relative variables."""
    if source_column is None:
        return True
    return (
        source_column not in NON_DISPLAYABLE_FACTOR_COLS
        and source_column not in BATCH_RELATIVE_COLS
    )


def format_value(name: str, value: object) -> str:
    """Render a **raw** feature value for display.

    Never pass a transformed (standardized or one-hot) value here: a z-score of
    -1.8 on `taux_rendu_devoirs` would be rendered as "-180 %".
    """
    if value is None:
        return "non renseigné"
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number:  # NaN
            return "non renseigné"
        base = _strip_prefix(str(name))
        if base == "taux_rendu_devoirs":
            return f"{number * 100:.0f} %"
        if base.endswith("_pct"):
            return f"{number:.0f} %"
        if base == "boursier":
            return "oui" if number >= 0.5 else "non"
        if float(number).is_integer():
            return f"{int(number)}"
        return f"{number:.2f}"
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return "non renseigné"
    return text
