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
- `train` : entraînement, validation, seuil métier, sérialisation et run MLflow.
- `predict` : scoring batch avec sortie CSV et persistance optionnelle.
- `init-db`, `medallion-load`, `purge-expired` : cycle BDD/RGPD.
- `drift-report` : rapport PSI.
- `model-register`, `model-promote`, `model-rollback` : cycle de vie contrôlé.
- `schedule` : contrôles planifiés ou exécution ponctuelle vérifiable.
- `serve` : API FastAPI.

**Implémentation API** :
- `GET /health`
- `GET /ready`
- `POST /predict`
- Authentification optionnelle par `DECROCHAGE_API_KEY` / `X-API-Key`.
- Limitation de débit configurable sur les routes sensibles.
- Journal structuré sans payload et corrélation par `X-Request-ID`.

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
- `compose.yaml` fournit Postgres + API et un profil Run avec Caddy, APScheduler, Prometheus et Grafana.

**CI** :
- `.github/workflows/ci.yml` exécute lint, formatage, tests et build Docker.
- Les secrets restent hors Git (`.env.example` documente les variables attendues, `.env` local reste ignoré).

**Preuves** :
- `Dockerfile`
- `compose.yaml`
- `.github/workflows/ci.yml`
- `tests/test_certification_artifacts.py`

## 5. Suivi MLflow et registre

**Objectif** : relier une expérience reproductible à chaque candidat et séparer entraînement, validation et promotion.

**Implémentation** :
- `tracking.track_training_result` ouvre un run dans `decrochage-l1-training`.
- Paramètres, métriques scalaires, rapport JSON et bundle joblib sont enregistrés comme preuves.
- Le registre utilise les alias `candidate`, `production` et `archived`.
- La promotion exige les seuils techniques puis une approbation humaine explicite.

**Preuves** :
- `src/decrochage/tracking.py`
- `src/decrochage/registry.py`
- `tests/test_tracking.py`
- `tests/test_registry.py`

## 6. Drift PSI et ordonnancement

**Objectif examen** : couvrir C9 avec une surveillance simple, compréhensible et chiffrée.

**Implémentation** :
- `monitoring.population_stability_index` calcule le PSI sur variables numériques.
- `monitoring.classify_psi` applique les seuils : `watch >= 0.10`, `alert >= 0.25`.
- `monitoring.build_drift_report` produit un rapport JSON compact.
- `decrochage drift-report` écrit le rapport et peut le persister dans `gold_drift_report`.
- Le service APScheduler exécute le contrôle de dérive puis évalue chaque semaine la politique de réentraînement, dont l'échéance annuelle est un déclencheur.
- Un réentraînement justifié produit uniquement un candidat ; la production n'est jamais promue automatiquement.
- L'état atomique empêche les doublons après redémarrage le même jour et le heartbeat détecte le silence.

**Preuves** :
- `src/decrochage/monitoring.py`
- `tests/test_monitoring.py`
- `tests/test_scheduler.py`
- `docs/monitoring_plan.md`
- Notebook §13.

## 7. Observabilité Grafana

**Objectif** : rendre l'état du service visible et actionnable.

**Implémentation** :
- Prometheus collecte `/metrics`.
- Le dashboard provisionné affiche disponibilité, débit, erreurs 5xx, latence p95 et statuts HTTP.
- Les alertes attendent cinq minutes avant notification et pointent vers le runbook.

**Preuves** :
- `monitoring/grafana/provisioning/dashboards/json/decrochage-run.json`
- `monitoring/grafana/provisioning/alerting/rules.yml`
- `reports/screenshots/docker/grafana-dashboard.png`
- `reports/screenshots/docker/grafana-alert-rules.png`
- `reports/screenshots/docker/prometheus-targets.png`
- `reports/screenshots/docker/caddy-https-api.png`
- `docs/runbook.md`

**Frontière notebook / exploitation** : le notebook démontre la préparation des données,
l'entraînement, l'évaluation et l'explicabilité. Il ne peut pas, à lui seul, prouver
le routage HTTPS, la collecte périodique des métriques, le chargement d'un dashboard
provisionné ou l'évaluation continue des alertes. Ces éléments nécessitent les services
Docker en fonctionnement et sont documentés par des captures Playwright de l'exécution réelle.

## 8. Model Card / Threat Model

**Objectif examen** : documenter l'usage prévu, les limites et les risques opérationnels/sécurité.

**Model Card** :
- Usage prévu : aide à la priorisation d'accompagnement à mi-S1.
- Hors périmètre : décision automatique, sanction, usage hors L1 sans revalidation.
- Limites : données synthétiques, revalidation réelle nécessaire.
- Éthique : sous-groupes, décision humaine, minimisation.

**Threat Model** :
- Surface : API FastAPI de scoring.
- Menaces : spoofing, tampering, repudiation, information disclosure, DoS, elevation of privilege.
- Contrôles : API key, validation Pydantic, limite de débit, `X-Request-ID`, journal sans payload, non-root, rétention et pseudonymisation.
- Gates réelles : stockage de secrets, chiffrement au repos et validation DPO avant données réelles.

**Preuves** :
- `docs/model_card.md`
- `docs/threat_model.md`
- `docs/rgpd_accountability.md`

## 9. Matrice C1 → C9

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
5. MLflow et ordonnanceur : tracer les expériences et produire des candidats contrôlés.
6. Drift PSI et Grafana : surveiller les données et le service.
7. Model card / threat model : documenter usage, limites et risques.
8. Matrice C1 → C9 : prouver la conformité au référentiel.
