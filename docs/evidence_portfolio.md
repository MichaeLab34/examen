# Portefeuille de preuves du projet

Ce document relie les ajouts demandés aux preuves concrètes du dépôt. Il complète le notebook certifiant sans le remplacer : le notebook reste le livrable principal, ce fichier sert de table d'orientation pour la soutenance et la relecture.

## 1. RGPD / pseudonymisation

**Objectif examen** : montrer que les données étudiantes sont traitées comme des données personnelles sensibles, avec minimisation, finalité limitée, décision humaine et traçabilité.

**Implémentation** :
- `src/decrochage/persistence.py` impose `DECROCHAGE_PSEUDONYMIZATION_SECRET` avant toute persistance étudiante.
- Les identifiants directs `student_id` et `id_dossier` sont HMAC-SHA-256 à partir de Silver.
- Bronze garde le brut uniquement pour traçabilité restreinte ; Silver et Gold ne propagent pas les identifiants directs en clair.
- `privacy_audit_log` trace les chargements et purges.
- `docs/rgpd_accountability.md` documente finalité, minimisation, rétention, sécurité et accountability.

**Preuves** :
- `tests/test_persistence.py::test_bronze_keeps_raw_identifiers_and_silver_gold_are_pseudonymized`
- `tests/test_persistence.py::test_persisting_student_data_requires_pseudonymization_secret`
- Notebook §4 et §10-11.

## 2. Médaillon Bronze / Silver / Gold

**Objectif examen** : structurer le cycle de vie des données et séparer données brutes, données nettoyées et dataset de modélisation.

**Implémentation** :
- Bronze : `bronze_student_raw`, `bronze_catalogue_raw` conservent les payloads sources avec `batch_id`, `parse_ok`, `rejected_reason`.
- Silver : `silver_student`, `silver_catalogue` stockent les lignes nettoyées/normalisées/pseudonymisées.
- Gold : `gold_training_feature`, `gold_prediction`, `gold_drift_report` stockent features anti-fuite, scores et monitoring.
- CLI : `uv run decrochage init-db` puis `uv run decrochage medallion-load ...`.

**Preuves** :
- `src/decrochage/persistence.py`
- `tests/test_persistence.py::test_initialize_database_and_persist_medallion_layers`
- `ARCHITECTURE_PROJET.md`
- Notebook §7, §10, §11.

## 3. API / CLI

**Objectif examen** : prouver que la solution ne vit pas seulement dans un notebook, mais possède un chemin d'exploitation rejouable.

**Implémentation CLI** :
- `check-data` : qualité, jointure catalogue, garde-fou anti-fuite.
- `train` : entraînement, validation, seuil métier et sérialisation.
- `predict` : scoring batch avec sortie CSV et persistance optionnelle.
- `init-db`, `medallion-load`, `purge-expired` : cycle BDD/RGPD.
- `drift-report` : rapport PSI.
- `serve` : API FastAPI.

**Implémentation API** :
- `GET /health`
- `GET /ready`
- `POST /predict`
- Authentification optionnelle par `DECROCHAGE_API_KEY` / `X-API-Key`.

**Preuves** :
- `src/decrochage/cli.py`
- `src/decrochage/api.py`
- `tests/test_api.py`
- `tests/test_serving.py`
- Notebook §10.

## 4. Docker / CI

**Objectif examen** : démontrer un minimum d'industrialisation reproductible et contrôlée.

**Docker** :
- `Dockerfile` construit une image de serving Python 3.13.
- L'image tourne avec un utilisateur non-root `appuser`.
- `compose.yaml` fournit Postgres + API locale avec secrets exigés via variables d'environnement.

**CI** :
- `.github/workflows/ci.yml` exécute lint, formatage, tests et build Docker.
- Les secrets restent hors Git (`.env.example` documente les variables attendues, `.env` local reste ignoré).

**Preuves** :
- `Dockerfile`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `tests/test_certification_artifacts.py`

## 5. Drift PSI

**Objectif examen** : couvrir C9 avec une surveillance simple, compréhensible et chiffrée.

**Implémentation** :
- `monitoring.population_stability_index` calcule le PSI sur variables numériques.
- `monitoring.classify_psi` applique les seuils : `watch >= 0.10`, `alert >= 0.25`.
- `monitoring.build_drift_report` produit un rapport JSON compact.
- `decrochage drift-report` écrit le rapport et peut le persister dans `gold_drift_report`.

**Preuves** :
- `src/decrochage/monitoring.py`
- `tests/test_monitoring.py`
- `docs/monitoring_plan.md`
- Notebook §13.

## 6. Model Card / Threat Model

**Objectif examen** : documenter l'usage prévu, les limites et les risques opérationnels/sécurité.

**Model Card** :
- Usage prévu : aide à la priorisation d'accompagnement à mi-S1.
- Hors périmètre : décision automatique, sanction, usage hors L1 sans revalidation.
- Limites : données synthétiques, revalidation réelle nécessaire.
- Éthique : sous-groupes, décision humaine, minimisation.

**Threat Model** :
- Surface : API FastAPI de scoring.
- Menaces : spoofing, tampering, repudiation, information disclosure, DoS, elevation of privilege.
- Contrôles : API key, validation Pydantic, non-root container, pas de payload logging, rétention, pseudonymisation.

**Preuves** :
- `docs/model_card.md`
- `docs/threat_model.md`
- `docs/rgpd_accountability.md`

## 7. Matrice C1 → C9

**Objectif examen** : rendre la couverture des compétences explicite pour ne pas laisser le jury deviner.

**Implémentation** :
- `docs/competences_c1_c9.md` mappe chaque compétence vers les preuves et la phrase à défendre à l'oral.
- Le README pointe vers cette matrice.

**Preuves** :
- `docs/competences_c1_c9.md`
- `README.md`
- `tests/test_certification_artifacts.py`

## Priorité de présentation

En soutenance, ne pas présenter ces ajouts comme une usine technique. Les présenter comme une chaîne cohérente :

1. RGPD / pseudonymisation : protéger les données étudiantes.
2. Médaillon Bronze / Silver / Gold : tracer et séparer les responsabilités.
3. API / CLI : rejouer hors notebook.
4. Docker / CI : reproduire et vérifier.
5. Drift PSI : surveiller après déploiement.
6. Model card / threat model : documenter usage, limites et risques.
7. Matrice C1 → C9 : prouver la conformité au référentiel.
