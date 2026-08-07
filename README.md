# Détection précoce du décrochage étudiant en L1

Cas d'usage de la certification **« Concevoir et implémenter une solution
d'intelligence artificielle »**. Objectif : à mi-parcours du premier semestre,
prédire le **risque de décrochage** (`abandon`, classification binaire) d'un
étudiant de L1 et estimer sa **moyenne finale attendue** (`moyenne_finale`,
régression secondaire), afin de prioriser les dispositifs d'accompagnement.

Le livrable central est un **notebook unique et exécutable**
(`notebooks/decrochage_etudiant.ipynb`) couvrant les compétences C1 → C9, avec
journal de bord à chaque grande étape. Le journal détaillé au jour le jour
(décisions, difficultés, arbitrages) est tenu à part dans
`notebooks/journal_de_bord.ipynb` et fait partie des livrables.

## Structure

```text
examen/
├── pyproject.toml              # projet uv (Python 3.13) + dépendances
├── ARCHITECTURE_PROJET.md      # architecture technique de la solution
├── README.md
├── data/
│   ├── raw/                    # données brutes fournies (3 CSV) — livrable
│   └── processed/              # espace transitoire ignoré ; la cible est la BDD
├── notebooks/
│   ├── decrochage_etudiant.ipynb   # notebook certifiant (plan imposé 0→15)
│   └── journal_de_bord.ipynb       # journal de bord détaillé, jour par jour
├── src/decrochage/            # code réutilisable & reproductible
│   ├── preprocessing.py        # parsing données sales, normalisation, dédoublonnage
│   ├── features.py             # périmètre de scoring anti-fuite + feature engineering
│   ├── training.py             # entraînement industrialisé train/validation/test
│   ├── serving.py              # bundle modèle + fonction predict (contrat C6)
│   ├── monitoring.py           # rapport de dérive PSI (C9)
│   ├── operations.py           # politique Run : réentraînement + barrière de promotion
│   ├── registry.py             # alias MLflow candidate/production/archived
│   ├── tracking.py             # runs MLflow : paramètres, métriques, artefacts
│   ├── alerting.py             # anti-spam + heartbeat des tâches planifiées
│   ├── scheduler.py            # contrôles de dérive et réentraînement planifiés
│   ├── persistence.py          # persistance SQL + couches Bronze/Silver/Gold
│   ├── api.py                  # API FastAPI /health /ready /predict
│   ├── portal/                 # portail de restitution aux référents (/portal)
│   └── cli.py                  # commandes batch et service
├── docs/                       # fiche modèle, industrialisation, surveillance, menaces
├── tests/                      # tests unitaires et contrats API/service
├── artifacts/
│   ├── models/                 # bundle sérialisé (joblib)
│   └── figures/                # graphiques exportés
└── reports/                    # énoncé, slides + conducteur de soutenance
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
uv sync --group dev                       # installe les outils de qualité et tests
uv run jupyter lab                        # ouvre le notebook
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/decrochage_etudiant.ipynb
uv run decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
uv run decrochage init-db
uv run decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
uv run decrochage purge-expired
bash scripts/generate-local-certs.sh      # prérequis Caddy : certificats TLS locaux
docker compose --profile run up --build   # inclut MLflow sur http://localhost:5000
$training = uv run decrochage train data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv --tracking-uri http://localhost:5000 | ConvertFrom-Json
uv run decrochage model-register artifacts/models/model_bundle.joblib --run-id $training.mlflow.run_id --registry-uri http://localhost:5000
uv run decrochage model-promote 1 --approve --registry-uri http://localhost:5000
uv run decrochage retraining-decision reports/drift_report.json --trained-on 2025-07-01 --labels-available
uv run decrochage schedule --run-once monitoring
uv run decrochage serve                   # démarre l'API FastAPI
docker compose logs api --tail 20          # journaux JSON corrélés par request_id
uv run ruff check . ; uv run black --check . ; uv run pytest
```

## Portail de restitution

Le portail (`/portal`) est le maillon humain de la chaîne : il transforme les
scores persistés en liste de travail priorisée, explicable et auditée. Il est
**désactivé par défaut** — un déploiement d'inférence pur n'expose aucune page web.

```powershell
$env:DECROCHAGE_PORTAL_ENABLED = "true"
$env:DECROCHAGE_PORTAL_SECRET = "<32 octets hexadécimaux, hors Git>"
uv run decrochage init-db                 # crée aussi la table portal_user
uv run decrochage portal-user-add referent01 --role referent --filieres "Informatique,Gestion"
uv run decrochage serve                   # http://localhost:8000/portal/login
```

Trois rôles : `referent` (cohorte priorisée, fiche de risque, export),
`pilote` (indicateurs agrégés, simulation de seuil, export),
`auditeur` (journal de redevabilité, échéances de conservation — aucun score
individuel).

Trois garanties structurantes :

- **Aucun identifiant en clair.** Le portail ne manipule que les pseudonymes
  HMAC et ne détient aucune table de correspondance ; la ré-identification
  relève du SI scolarité, à partir d'un export à colonnes fermées.
- **Lecture seule.** Aucun scoring n'est déclenché depuis l'interface : toute
  prédiction affichée est rattachée à un lot d'ingestion auditable et purgeable.
- **Explicabilité exacte, pas approchée.** Sur la régression logistique retenue,
  la contribution d'une variable est `coefficient × valeur transformée` ; un test
  vérifie que ces contributions et l'ordonnée à l'origine somment exactement au
  log-odds du modèle. Aucune dépendance SHAP à l'exécution.

Le mot de passe n'est jamais accepté en argument de ligne de commande (saisie
masquée et confirmée), les empreintes sont Argon2id, et chaque consultation ou
export écrit un événement dans `privacy_audit_log`.

## Industrialisation

Le notebook reste le livrable certifiant. Le chemin d'exploitation léger est porté
par le package : entraînement avec seuil choisi sur validation, bundle joblib,
CLI, API FastAPI, portail de restitution, persistance SQL en architecture
médaillon, Dockerfile, CI GitHub Actions et rapport de dérive PSI. Le dispositif d'exploitation ajoute le cycle de vie complet :
reverse-proxy Caddy/HTTPS, métriques Prometheus, tableau de bord et alertes Grafana,
ordonnanceur APScheduler avec heartbeat, politique annuelle de réentraînement,
runs MLflow et promotion/rollback avec validation humaine. L'API ajoute une
limite de débit et des journaux corrélés par `X-Request-ID` sans données étudiantes. La stack Docker
Compose fournit une base Postgres locale ; `DECROCHAGE_DATABASE_URL` permet de viser une autre base
compatible SQLAlchemy. Toute persistance BDD pseudonymise les identifiants
directs à partir de Silver par HMAC-SHA-256 via
`DECROCHAGE_PSEUDONYMIZATION_SECRET` ; Bronze reste brut et doit donc être
restreint, audité et purgé. Voir
`docs/industrialisation.md`, `docs/rgpd_accountability.md`,
`docs/model_card.md`, `docs/monitoring_plan.md`, `docs/run_architecture.md`,
`docs/runbook.md`, `docs/threat_model.md`, `docs/competences_c1_c9.md` et
`docs/evidence_portfolio.md` pour la matrice de couverture et les preuves de
certification.

## Licence

Le code source, les tests et la documentation sont sous licence MIT (voir
[LICENSE](LICENSE)). Les jeux de données de `data/raw/` sont fournis par
l'organisme de certification et ne sont pas redistribuables ; l'énoncé du cas
d'usage n'est volontairement pas versionné.

## Données

Jeu principal `decrochage_etudiants_complet_V5.csv` (~5 200 lignes, 33 colonnes),
volontairement « brut » (doublons, nombres en texte, dates multi-formats,
encodages incohérents, texte libre). Table de référence
`catalogue_formations_V5.csv` jointe via `filiere`. Un échantillon de 50 lignes
est fourni pour lecture rapide.
