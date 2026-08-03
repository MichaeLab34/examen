# Plan de surveillance

## Signaux surveillés

| Signal | Métrique | Seuil d'alerte |
|---|---|---|
| Dérive des données | PSI sur les variables numériques | `watch >= 0.10`, `alert >= 0.25` |
| Performance du modèle | AUC / rappel quand les labels arrivent | AUC `< 0.85` ou baisse de rappel `> 10 pts` |
| Équité | Écarts de rappel et de taux d'alerte par sous-groupe | écart `> 10 pts` |
| Qualité des données | Taux de valeurs manquantes par variable clé | `> 20 %` |
| Exploitation | Disponibilité de l'API et taux d'erreur | `/ready` indisponible ou 5xx > 1 % pendant 5 min |
| Tâches planifiées | Signal de vie externe (*heartbeat*) | ping attendu absent |

## Cadence

- Par défaut, APScheduler lance le contrôle de dérive chaque lundi à 06:00
  (Europe/Paris) ; il peut aussi être exécuté par
  `decrochage schedule --run-once monitoring`.
- Pendant la fenêtre de scoring de mi-S1, les contrôles de qualité des données et
  de dérive tournent en plus sur chaque lot importé.
- Chaque mois, l'équipe passe en revue le taux d'alerte, les métriques par
  sous-groupe, les incidents non résolus et les retours des équipes
  d'accompagnement.
- APScheduler évalue la politique de réentraînement chaque lundi à 07:00. La
  dérive, la performance ou la revue annuelle peuvent déclencher un candidat,
  mais uniquement si des labels récents sont disponibles ; la comparaison avec la
  production et l'approbation humaine suivent.

## Actions

1. Enquêter sur un changement de collecte des données quand le PSI passe en `watch`.
2. Geler la réutilisation automatique et déclencher une revue du modèle quand le
   PSI passe en `alert` ; sans labels récents, enquêter sur la collecte plutôt que
   de réentraîner à l'aveugle.
3. Recalibrer le seuil si la capacité d'intervention ou le rapport de coût FN/FP
   change.
4. Ne promouvoir qu'après non-régression du rappel, AUC >= 0,85, écart de rappel
   entre sous-groupes <= 10 points et approbation humaine explicite.
5. Revenir en arrière sur l'alias MLflow `production` quand un modèle validé
   régresse en exploitation.

## Acheminement des alertes

Grafana achemine les avertissements d'exploitation vers le canal de l'équipe
universitaire et attend cinq minutes continues avant de déclencher. Le circuit
d'astreinte DSI est réservé à la fenêtre de scoring de mi-S1, parce qu'il s'agit
d'un service batch rejouable, pas d'une API critique 24/7.
`DECROCHAGE_HEALTHCHECK_URL` couvre le silence des tâches de scoring, de dérive
et de purge.

## Persistance

Les rapports de dérive sont écrits en artefacts JSON et peuvent aussi être
stockés dans la table SQL `gold_drift_report`. L'état du planificateur est écrit
de façon atomique sous `artifacts/scheduler/state.json`, ce qui évite une double
exécution après un redémarrage le même jour. La décision de surveillance reste
ainsi rattachée à un `batch_id` d'ingestion, avec `status`, `watch_count`,
`alert_count` et le contenu complet du rapport disponibles pour les tableaux de
bord ou un audit ultérieur.
