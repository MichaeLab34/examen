# Architecture d'exploitation

## Décision en une phrase

Pour environ 5 200 étudiants par cohorte et un scoring surtout batch à mi-S1,
la cible proportionnée est un **VPS européen conteneurisé**, protégé par Caddy,
avec Postgres, Prometheus/Grafana et un registre MLflow local. Kubernetes serait
un surdimensionnement ; le serverless sera réévalué si l'usage devient très
irrégulier ou si l'université dispose déjà d'une plateforme managée.

## Architecture cible

```text
SI/LMS -> Caddy HTTPS -> FastAPI -> bundle MLflow @production
                         |    |
                         |    +-> Postgres Bronze/Silver/Gold
                         +------> /metrics -> Prometheus -> Grafana -> canal equipe

Jobs planifies (scoring, drift, purge) -> heartbeat externe (silence detecte)
Drift/performance/labels -> candidat -> gate rappel/AUC/equite -> validation humaine
                                                       |-> promotion ou rollback
```

Le VPS garde le traitement et les données sous le contrôle de la DSI. Les
conteneurs préservent la portabilité : changer d'hébergeur ne demande pas de
réécrire le service. Caddy fournit le reverse-proxy et renouvelle automatiquement
les certificats HTTPS avec un vrai nom de domaine.

## Coût Run et alternatives

Les montants ci-dessous sont des **ordres de grandeur à confirmer par la DSI**,
pas des devis fournisseurs.

| Option | Ordre de grandeur mensuel | Décision |
|---|---:|---|
| VPS production + sauvegarde + domaine | 10-20 EUR | Retenu pour le pilote |
| Petit environnement de test séparé | +5-10 EUR | Recommandé avant production |
| Serverless + base managée | 20-80 EUR | À revoir si trafic très intermittent |
| Kubernetes managé | 60-150 EUR avant services utiles | Écarté à cette échelle |

Le TCO inclut aussi le temps humain : revue mensuelle des alertes, revue annuelle
du modèle, validation DPO et test de restauration des sauvegardes. La haute
disponibilité n'est pas retenue sans SLA : une indisponibilité brève ne met pas
en danger un flux temps réel, car le scoring peut être rejoué.

## Maintenance du modèle

Le calendrier industriel mensuel du cours n'est pas adapté au décrochage : les
labels fiables arrivent après la cohorte. La politique livrée combine :

- contrôle drift/qualité à chaque batch ;
- investigation immédiate si PSI atteint `alert` ;
- entraînement annuel quand les nouvelles issues sont disponibles ;
- entraînement anticipé uniquement si dérive/performance et labels frais ;
- promotion semi-automatique après non-régression du rappel, AUC >= 0,85,
  écart de rappel entre sous-groupes <= 10 points et validation humaine.

MLflow conserve les versions et les alias `candidate`, `production`,
`archived`. Le rollback repointe `production` vers une version précédente.
L'API recharge ensuite l'alias via `POST /admin/reload`, protégé par la clé API.
Les bundles enregistrés depuis la racine utilisent un chemin relatif
`artifacts/...`, identique sur l'hôte et dans le conteneur `/app`.

## Alertes et silence

Le service expose `/metrics`. Grafana attend cinq minutes avant d'alerter sur
l'indisponibilité ou un taux de 5xx élevé, ce qui limite la fatigue d'alerte.
Le canal d'équipe suffit en journée ; l'astreinte DSI n'est activée que pendant
la fenêtre critique de scoring. Un heartbeat externe couvre l'angle mort d'une
tâche planifiée qui ne démarre plus et n'émet donc aucune erreur.

## Valeur et ROI responsable

Le projet ne dispose pas d'un coût institutionnel validé du décrochage. Le ROI
ne doit donc pas être inventé. Le pilote mesurera :

`valeur = étudiants utilement accompagnés x effet causal du dispositif`

Le coût à comparer comprend l'infrastructure, le temps des référents et les
fausses alertes. Un A/B test ou un déploiement progressif est nécessaire pour
estimer l'effet causal ; l'AUC seule ne prouve aucun gain social ou financier.
