# Détection précoce du décrochage étudiant en L1

Cas d'usage de la certification **« Concevoir et implémenter une solution
d'intelligence artificielle »**. Objectif : à mi-parcours du premier semestre,
prédire le **risque de décrochage** (`abandon`, classification binaire) d'un
étudiant de L1 et estimer sa **moyenne finale attendue** (`moyenne_finale`,
régression secondaire), afin de prioriser les dispositifs d'accompagnement.

Le livrable central est un **notebook unique et exécutable**
(`notebooks/decrochage_etudiant.ipynb`) couvrant les compétences C1 → C9, avec
journal de bord à chaque grande étape.

## Structure

```text
examen/
├── pyproject.toml              # projet uv (Python 3.13) + dépendances
├── ARCHITECTURE_PROJET.md      # architecture technique de la solution
├── README.md
├── data/
│   ├── raw/                    # données brutes fournies (3 CSV) — livrable
│   └── processed/              # données nettoyées régénérées par le notebook
├── notebooks/
│   └── decrochage_etudiant.ipynb   # notebook certifiant (plan imposé 0→15)
├── src/decrochage/            # code réutilisable & reproductible
│   ├── preprocessing.py        # parsing données sales, normalisation, dédoublonnage
│   ├── features.py             # périmètre de scoring anti-fuite + feature engineering
│   └── serving.py              # bundle modèle + fonction predict (contrat C6)
├── artifacts/
│   ├── models/                 # bundle sérialisé (joblib)
│   └── figures/                # graphiques exportés
└── reports/                    # énoncé, support de soutenance
```

## Points méthodologiques clés

- **Anti-fuite de données** : `moyenne_finale` et les identifiants
  (`student_id`, `id_dossier`) sont exclus des variables explicatives.
- **Anti-fuite temporelle** : `moyenne_partiels_s1` et `nb_ue_validees_s1`
  (consolidées en fin de S1) sont hors périmètre de scoring à mi-S1.
- **Leurres** : `groupe_td`, `couleur_carte_etudiante`, `jour_inscription` sont
  identifiés, discutés puis écartés.
- Le périmètre de scoring est verrouillé dans `features.scoring_feature_columns`
  et vérifié par `features.assert_no_leakage`.

## Commandes utiles

```powershell
uv sync --group notebook                 # installe l'environnement (Python 3.13)
uv run jupyter lab                        # ouvre le notebook
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/decrochage_etudiant.ipynb
uv run ruff check . ; uv run black --check .
```

## Données

Jeu principal `decrochage_etudiants_complet_V5.csv` (~5 200 lignes, 33 colonnes),
volontairement « brut » (doublons, nombres en texte, dates multi-formats,
encodages incohérents, texte libre). Table de référence
`catalogue_formations_V5.csv` jointe via `filiere`. Un échantillon de 50 lignes
est fourni pour lecture rapide.
