# Industrialisation

Le projet sépare le notebook certifiant du chemin opérationnel. Le notebook
explique le raisonnement C1-C9 ; le package sous `src/decrochage/` contient le
code réutilisable pour l'entraînement, la prédiction, l'exposition en API, les
opérations en ligne de commande et la surveillance.

## Points d'entrée opérationnels

- `decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  valide le nettoyage, la couverture de la jointure catalogue et les garde-fous
  anti-fuite.
- `decrochage init-db` crée les tables SQL utilisées par la persistance
  Bronze/Silver/Gold. Par défaut la base est `artifacts/decrochage.db`, tandis
  que la stack Docker proche de la production utilise Postgres.
- `decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  persiste les lignes brutes en Bronze, les lignes nettoyées et pseudonymisées en
  Silver, et les lignes de variables prêtes pour le ML en Gold.
- `decrochage purge-expired` supprime les lots ayant dépassé leur fenêtre de
  rétention RGPD.
- `decrochage train ... --output artifacts/models/model_bundle.joblib` entraîne un
  bundle avec séparation train/validation/test et enregistre paramètres,
  métriques et artefacts dans MLflow Tracking.
- `decrochage predict artifacts/models/model_bundle.joblib input.csv --output reports/predictions.csv`
  calcule les scores de dossiers SI/LMS bruts. Ajouter `--persist-db --batch-id <id>` pour
  stocker les prédictions dans la table Gold.
- `decrochage drift-report reference.csv current.csv --output reports/drift_report.json`
  produit un rapport de dérive PSI. Ajouter `--persist-db --batch-id <id>` pour
  stocker le résultat de surveillance dans la table Gold.
- `decrochage serve` démarre le service FastAPI.
- `decrochage retraining-decision ...` sépare l'enquête sur la dérive d'un
  réentraînement supervisé, qui exige des labels de cohorte récents.
- `decrochage model-register --run-id <run-id>`, `model-promote --approve` et `model-rollback`
  mettent en œuvre le cycle de vie des alias MLflow, avec une barrière de
  promotion humaine.
- `decrochage alert-decision` applique la temporisation et l'hystérésis ;
  `heartbeat` signale qu'un batch planifié s'est effectivement terminé.
- `decrochage schedule` démarre le démon APScheduler. Utiliser `--run-once
  monitoring` ou `--run-once retraining` pour une exécution manuelle auditable.

## Base de données et architecture médaillon

La couche de persistance est implémentée dans `src/decrochage/persistence.py`
avec SQLAlchemy. `DECROCHAGE_DATABASE_URL` peut pointer vers un autre moteur SQL ;
quand elle n'est pas définie, SQLite est utilisé en local. Pour une stack locale
proche de la production, utiliser Postgres via Docker Compose :

```bash
cp .env.example .env
# renseigner POSTGRES_PASSWORD et DECROCHAGE_PSEUDONYMIZATION_SECRET
docker compose up -d postgres
uv run decrochage init-db
uv run decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
```

La base locale contient des dossiers étudiants et est volontairement ignorée par
Git. Le secret de pseudonymisation doit rester hors du gestionnaire de versions.

## Suivi et registre MLflow

Docker Compose expose MLflow sur `http://localhost:5000`. Ses métadonnées
utilisent un moteur de stockage SQLite isolé sous `artifacts/mlflow-server/` ; la base
applicative reste dédiée aux données métier. Le serveur stocke les paramètres et
métriques des runs, le rapport d'entraînement JSON et le bundle de modèle
sérialisé. L'enregistrement exige le `run_id` d'origine, si bien que chaque
version de modèle reste rattachée à son expérience.

L'API et le planificateur utilisent `http://mlflow:5000` à l'intérieur de Docker.
Une fois une première version promue, définir
`DECROCHAGE_REGISTERED_MODEL=decrochage-l1` ; `/ready` rapporte alors l'alias
actif et la version chargée depuis le registre.

- Les tables Bronze conservent un payload brut par ligne source, avec les champs
  `batch_id`, `parse_ok` et `rejected_reason` pour la traçabilité. Cette couche
  peut contenir des identifiants directs : elle doit donc être restreinte,
  auditée et purgée.
- Les tables Silver stockent les enregistrements nettoyés et normalisés de façon
  déterministe, ainsi que les références catalogue. Les identifiants directs y
  sont remplacés par des pseudonymes HMAC-SHA-256 déterministes.
- Les tables Gold stockent les variables d'entraînement sans colonnes de fuite,
  les libellés de découpage `train`/`validation`/`test` déterministes, les
  prédictions et les rapports de dérive.
- `privacy_audit_log` stocke les événements de redevabilité sans donnée
  étudiante directe.

La première séquence opérationnelle est :

```bash
decrochage init-db
decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
```

Réutiliser le `batch_id` renvoyé lors de la persistance des prédictions ou des
rapports de dérive en aval.

## Contrat d'API

- `GET /health` : vivacité, renvoie 200 tant que le processus tourne.
- `GET /ready` : disponibilité, renvoie 200 uniquement quand le bundle de modèle
  est chargé.
- `POST /predict` : accepte des dossiers étudiants bruts et renvoie
  `proba_abandon` ainsi que `alerte`.
- `GET /metrics` : métriques Prometheus de disponibilité, d'erreurs et de latence.
- `POST /admin/reload` : recharge l'alias `production` configuré sans
  redéploiement de code ; cette route exige toujours `DECROCHAGE_API_KEY`.
- Chaque réponse porte un `X-Request-ID` ; les journaux structurés contiennent la
  route, le statut et la durée, jamais les payloads ni les clés d'API.
- Les journaux d'exécution sont émis en un objet JSON par ligne sur la sortie
  d'erreur du conteneur. Le pilote de journalisation Docker `json-file` les fait
  tourner à 10 Mo et en conserve cinq fichiers au maximum.
- `/predict` et `/admin/reload` appliquent `DECROCHAGE_RATE_LIMIT_PER_MINUTE` par
  client. Un déploiement multi-instances exige un limiteur partagé, porté par le
  frontal.

Définir `DECROCHAGE_MODEL_PATH` pour choisir le bundle de modèle. Définir
`DECROCHAGE_API_KEY` pour exiger un en-tête `X-API-Key`. Définir
`DECROCHAGE_PSEUDONYMIZATION_SECRET` avant toute persistance de lignes Silver,
Gold ou de prédictions.

## Déploiement

Construire et lancer en local :

```bash
docker compose up --build
```

Lancer la stack opérationnelle complète (planificateur, Caddy, Prometheus et
Grafana inclus) :

```bash
docker compose --profile run up --build
```

Grafana provisionne le tableau de bord `Décrochage L1 - Run API` et ses règles
d'alerte depuis des fichiers versionnés sous
`monitoring/grafana/provisioning`.

La recommandation de production, le TCO indicatif, les alternatives et les
arbitrages d'exploitation sont documentés dans `docs/run_architecture.md` ; les
actions en cas d'incident sont dans `docs/runbook.md`.

C'est volontairement une image de service légère : ni serveur de notebook, ni
ressources de présentation. La persistance en base est prise en charge par la
couche SQLAlchemy et peut utiliser le SQLite local par défaut ou le service
Postgres de Compose.
