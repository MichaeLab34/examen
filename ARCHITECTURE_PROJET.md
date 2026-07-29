# Architecture technique — Détection précoce du décrochage étudiant

Document d'architecture de la solution d'IA (compétence **C7**). Il décrit
l'organisation du code, les flux de données, les modules et les contraintes.

## Informations générales

| Champ | Valeur |
|---|---|
| Nom du projet | `decrochage` |
| Type de projet | ML — classification binaire (`abandon`) + régression secondaire (`moyenne_finale`) |
| Langage principal | `Python` |
| Environnement d'exécution | `Python 3.13` |
| Gestionnaire de dépendances | `uv` |
| Point d'entrée principal | Notebook `notebooks/decrochage_etudiant.ipynb` + package `decrochage` |
| Environnement cible | Batch local / conteneur (scoring semestriel à mi-S1, contrôles de dérive hebdomadaires) |

## Vue d'ensemble

Socle applicatif dans `src/decrochage/` (code déterministe reproductible),
notebook certifiant unique comme restitution de bout en bout, données brutes
immuables sous `data/raw/`, artefacts générés (modèle, figures) sous
`artifacts/`. L'architecture doit rendre lisibles : l'entrée des données
(SI scolarité + LMS + catalogue), les couches de préparation anti-fuite,
l'inférence (probabilité de décrochage) et la restitution aux référents.

## Arborescence

```text
examen/
├── pyproject.toml              # projet uv (Python 3.13), dépendances, outils
├── uv.lock                     # versions résolues
├── .python-version             # 3.13
├── .gitignore
├── ARCHITECTURE_PROJET.md      # ce document (C7)
├── README.md
├── data/
│   ├── raw/                    # 3 CSV fournis (immuables, livrables)
│   └── processed/              # espace transitoire ignoré ; la cible est la BDD
├── notebooks/
│   ├── decrochage_etudiant.ipynb   # notebook certifiant (plan imposé 0→15)
│   └── journal_de_bord.ipynb       # journal de bord détaillé, jour par jour
├── src/decrochage/            # package réutilisable
│   ├── __init__.py
│   ├── preprocessing.py        # parsing (%, virgules, km), dates, normalisation, dédoublonnage
│   ├── features.py             # périmètre anti-fuite + jointure catalogue + feature engineering
│   ├── training.py             # entraînement train/validation/test + seuil métier
│   ├── serving.py              # ModelBundle (joblib) + contrat predict (C6)
│   ├── monitoring.py           # dérive PSI + rapport JSON (C9)
│   ├── operations.py           # politique de réentraînement + barrière de promotion
│   ├── registry.py             # alias MLflow candidate/production/archived
│   ├── tracking.py             # runs MLflow : paramètres, métriques, artefacts
│   ├── alerting.py             # anti-spam + heartbeat des tâches planifiées
│   ├── scheduler.py            # contrôles de dérive et réentraînement planifiés
│   ├── persistence.py          # persistance SQL + couches Bronze/Silver/Gold
│   ├── ecodesign.py            # mesure des émissions + coût par point de performance
│   ├── logging_config.py       # journaux JSON structurés
│   ├── schemas.py              # schémas Pydantic du contrat d'API
│   ├── api.py                  # FastAPI : /health, /ready, /predict, /metrics, /admin/reload
│   ├── portal/                 # portail de restitution aux référents (bloc C7 « Restitution »)
│   │   ├── config.py           # PortalSettings (activation, secret de session, plafonds)
│   │   ├── models.py           # PortalUser : comptes d'agents, rôles, périmètre de filières
│   │   ├── security.py         # Argon2id, cookie signé, CSRF, verrouillage des tentatives
│   │   ├── repository.py       # lectures SQL, périmètre fail-closed, liste blanche de restitution
│   │   ├── labels.py           # libellés métier des variables du modèle
│   │   ├── routes.py           # routes /portal : cohorte, fiche, export, pilotage, conformité
│   │   ├── templates/          # gabarits Jinja2 (rendu serveur, auto-échappement)
│   │   └── static/             # CSS + amélioration progressive (aucune ressource distante)
│   └── cli.py                  # 19 commandes : données, BDD, entraînement, scoring, Run, comptes portail
├── tests/                      # contrats package/API + non-régression anti-fuite
├── docs/                       # fiche modèle, industrialisation, surveillance, menaces
├── Dockerfile                  # image de service non-root
├── artifacts/
│   ├── models/                 # model_bundle.joblib
│   └── figures/                # PNG exportés par le notebook
└── reports/                    # énoncé, slides + conducteur de soutenance
```

## Diagramme d'architecture (ingestion → features → inférence → restitution)

```text
   +----------------+   +------------------+   +-------------------+
   | SI Scolarité   |   |      LMS         |   | Catalogue         |
   | état civil,    |   | connexions,      |   | formations        |
   | bac, bourse    |   | heures, rendus   |   | (référence)       |
   +--------+-------+   +--------+---------+   +---------+---------+
            |                    |                       |
            +---------+----------+-----------------------+
                      v
          +---------------------------+   Extraction planifiée (mi-S1)
          |  Ingestion / consolidation|   1 ligne = 1 étudiant
          +------------+--------------+
                       v
          +---------------------------+   decrochage.preprocessing + features
          |  Préparation & features   |   parsing, normalisation, jointure,
          |  (périmètre anti-fuite)   |   feature engineering, verrou fuite
          +------------+--------------+
                       v
          +---------------------------+   ModelBundle (joblib) :
          |   Inférence (scoring)     |   Pipeline + seuil + catalogue
          |   predict_proba_abandon   |   → proba_abandon + alerte
          +------------+--------------+
                       v
          +---------------------------+   Portail /portal (decrochage.portal) :
          |  Restitution & pilotage   |   liste priorisée + facteurs contributifs
          |  (décision HUMAINE)       |   RBAC 3 rôles, audit de chaque consultation,
          |                           |   export pseudonymisé vers le SI scolarité
          +------------+--------------+
                       v
          +---------------------------+
          |  Surveillance & MLOps (C9)|   dérive, performance, ré-entraînement
          +---------------------------+
```

## Flux principaux

### Flux d'entraînement (notebook)

```text
data/raw/*.csv
   → clean_raw (dédoublonnage, parsing nombres/dates, normalisation)
   → enrich_with_catalogue (jointure filiere)
   → add_engineered_features (taux de rendu, intensité LMS, ...)
   → scoring_feature_columns + assert_no_leakage (verrou anti-fuite)
   → découpage stratifié train/validation/test
   → Pipeline(impute+encode+scale+LogReg), GridSearchCV (AUC)
   → seuil par minimisation du coût métier sur validation (FN:FP)
   → sérialisation ModelBundle (joblib)
```

### Flux d'inférence (production)

```text
DataFrame brut (SI+LMS)
   → serving.prepare_features (clean_raw + jointure catalogue embarqué + features)
   → bundle.pipeline.predict_proba
   → proba_abandon + alerte (seuil)
   → CLI batch ou API FastAPI
   → restitution priorisée aux référents (décision humaine)
```

## Modules applicatifs

| Module | Responsabilité | Entrées | Sorties |
|---|---|---|---|
| `decrochage.preprocessing` | Nettoyage déterministe des données brutes | DataFrame brut | DataFrame typé/normalisé |
| `decrochage.features` | Périmètre de scoring anti-fuite, jointure catalogue, feature engineering | DataFrame nettoyé | Features + garde-fous |
| `decrochage.training` | Entraînement industrialisé + choix du seuil sur validation | CSV bruts + catalogue | `ModelBundle`, métriques test |
| `decrochage.serving` | Bundle sérialisable + contrat de prédiction | Bundle, DataFrame brut | `proba_abandon`, `alerte` |
| `decrochage.api` | Service HTTP contractuel | Enregistrements JSON bruts | JSON prédictions |
| `decrochage.cli` | Exploitation batch | CSV / bundle | rapports, prédictions, service |
| `decrochage.monitoring` | Détection de dérive PSI | référence + courant | rapport JSON |
| `decrochage.portal` | Restitution aux référents : liste priorisée, explication locale, export SI, pilotage, conformité | Tables Gold/Silver + bundle chargé | Pages HTML, export CSV pseudonymisé, événements d'audit |
| `notebooks/…` | Restitution certifiante bout-en-bout (C1→C9) | Données + package | Analyses, modèle, figures |

## Contrats d'entrée / sortie

| Contrat | Format | Producteur | Consommateur | Validation |
|---|---|---|---|---|
| Données étudiants | CSV brut (33 colonnes) | SI scolarité / LMS | `preprocessing.clean_raw` | dictionnaire de données, bornes |
| Catalogue formations | CSV (7 colonnes) | Référentiel filières | `features.enrich_with_catalogue` | jointure `filiere` (100 %) |
| Score de risque | DataFrame `{proba_abandon: float∈[0,1], alerte: 0/1}` | `serving.predict_proba_abandon` | Tableau de bord référents | seuil documenté |
| API de prédiction | JSON `{records: [...]}` | FastAPI `/predict` | SI / tableau de bord | Pydantic + readiness |
| Rapport de dérive | JSON PSI par variable | `monitoring.build_drift_report` | Data scientist / DPO | seuils watch/alert |
| Liste de travail référent | HTML `/portal/cohorte` (pseudonymes, rang, probabilité, alerte) | `decrochage.portal` | Référent pédagogique | RBAC + périmètre de filières en SQL |
| Export vers le SI | CSV à colonnes fermées (`pseudo_id`, `rang`, `proba_abandon`, `alerte`, `filiere`, `batch_id`, `model_version`, `threshold`, `generated_at`) | `decrochage.portal` | SI scolarité (ré-identification) | plafond de lignes, export audité |

## Stockage et données

| Stockage | Rôle | Données | Rétention | Sensibilité |
|---|---|---|---|---|
| `data/raw/` | Données sources | 3 CSV fournis | Année universitaire | Sensible (scolaire) |
| `data/processed/` | Espace transitoire local | Exports ponctuels ignorés par Git | À supprimer après usage | Sensible |
| Postgres / `artifacts/decrochage.db` | Médaillon BDD | Bronze brut restreint ; Silver/Gold pseudonymisés | `DECROCHAGE_RETENTION_DAYS` | Sensible, source opérationnelle |
| `artifacts/models/` | Modèle sérialisé | `model_bundle.joblib` | Versionné | Interne |

## Contraintes (C7)

| Type | Contrainte | Réponse |
|---|---|---|
| Technique | ~5 200 étudiants/an, latence non critique | Scoring batch semestriel, modèle linéaire léger |
| RGPD | Données scolaires sensibles | Finalité limitée, pseudonymisation HMAC, rétention, audit log, décision humaine, information étudiants |
| Éco-conception | Sobriété du calcul, mesurée et non affirmée | Coût d'entraînement instrumenté (`ecodesign.py`, CodeCarbon) : le boosting coûte un ordre de grandeur de calcul de plus que la régression logistique (facteur ~10 pour le boosting, ~20 à 30 pour Random Forest selon la charge machine) pour une AUC équivalente ou inférieure. Leviers par impact décroissant : réentraînement **annuel** (et non mensuel), modèle linéaire, machine unique sans orchestrateur, minimisation des variables, scoring par batch semestriel, purge à échéance |
| Organisationnelle | Adoption équipes | Explicabilité (coefficients, SHAP), score = aide ; portail de restitution lisible par un non-technicien, avec facteurs contributifs par étudiant |
| Économique | Budget d'accompagnement limité | Priorisation par score (top-K) selon capacité tuteurs |

## Socle technique

| Besoin | Outil | Rôle |
|---|---|---|
| Environnement / dépendances | `uv` | Verrouillage des versions, exécution, packaging |
| Packaging | `pyproject.toml` + organisation `src/` | Package `decrochage` installable |
| Data / ML | `pandas`, `numpy`, `scikit-learn`, `xgboost` | Préparation, modèles, métriques |
| Explicabilité | `shap`, `permutation_importance` | Facteurs de risque |
| Sérialisation | `joblib` | Bundle modèle |
| API / CLI | `FastAPI`, `Typer`, `Pydantic` | Exploitation hors notebook |
| Surveillance | PSI pandas/numpy | Détection de dérive des données |
| Déploiement | Docker | API locale conteneurisée |
| Restitution | `jupyter`, `matplotlib`, `seaborn` | Notebook certifiant, visualisations |
| Portail | `Jinja2` (rendu serveur), `itsdangerous` (cookie signé), `argon2-cffi` (hachage) | Restitution aux référents sans chaîne de build JavaScript ni ressource distante |
| Qualité | `ruff`, `black`, `pytest`, GitHub Actions | Lint, formatage, tests, CI |

## Points d'attention

- Le **périmètre de scoring anti-fuite** (`features.scoring_feature_columns` +
  `assert_no_leakage`) est le verrou central : toute nouvelle variable doit être
  qualifiée (disponible à mi-S1 ? non identifiante ? non-leurre ?) avant ajout.
- Le **bundle** embarque le catalogue pour être auto-suffisant à l'inférence.
- Les performances rapportées valent sur **données synthétiques** ; revalidation
  sur données réelles + A/B test avant tout déploiement.
- Le **portail est désactivé par défaut** (`DECROCHAGE_PORTAL_ENABLED=false`) et
  refuse de démarrer sans `DECROCHAGE_PORTAL_SECRET` : un déploiement d'inférence
  pur n'expose aucune surface web authentifiée.
- Le portail est en **lecture seule** et ne déclenche aucun scoring : toute
  prédiction reste rattachée à un lot d'ingestion auditable et purgeable.
- L'explicabilité servie par le portail est **analytique** (`coefficient × valeur
  transformée`), donc exacte pour un modèle linéaire, sans dépendance SHAP à
  l'exécution. Un test vérifie que la somme des contributions et de l'ordonnée à
  l'origine égale le log-odds du modèle.
