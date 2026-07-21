# Runbook d'exploitation

## API indisponible

1. Vérifier `docker compose ps` puis les journaux `docker compose logs api`.
2. Tester `/health` puis `/ready` : le premier valide le processus, le second le modèle.
3. Vérifier le montage `artifacts/`, l'alias MLflow `production` et Postgres.
4. Si la nouvelle version est en cause, exécuter `decrochage model-rollback <version>`.
5. Recharger l'alias avec `POST /admin/reload` et documenter l'incident.

## Erreurs 5xx

1. Identifier la route et l'heure dans Grafana et les journaux API.
2. Contrôler le schéma des entrées SI/LMS et le nombre de lignes par requête.
3. Vérifier que le bundle et son catalogue se chargent hors API.
4. Suspendre le batch si les erreurs persistent ; ne jamais produire une liste partielle silencieuse.

## Dérive PSI

1. Lire les variables en `alert` dans le rapport JSON/Gold.
2. Vérifier d'abord un changement de collecte ou de définition métier.
3. Sans labels frais : investiguer, ne pas réentraîner à l'aveugle.
4. Avec labels frais : entraîner un candidat puis appliquer le gate rappel/AUC/équité.

## Job silencieux

1. Le heartbeat absent déclenche l'alerte externe.
2. Vérifier le planificateur, l'espace disque et les secrets.
3. Rejouer le job de façon idempotente et confirmer le nombre de lignes Gold.
4. Envoyer `decrochage heartbeat` seulement après validation complète du job.
