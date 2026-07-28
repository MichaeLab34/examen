# Architecture d'exploitation

## Décision en une phrase

Pour environ 5 200 étudiants par cohorte et un scoring surtout batch à mi-S1, la
cible proportionnée est une **machine unique conteneurisée**, protégée par Caddy,
avec Postgres, Prometheus/Grafana et un registre MLflow local.

**Option privilégiée : le serveur qui héberge déjà le LMS.** Les données
d'engagement en proviennent ; les traiter sur place évite tout transfert hors du
système d'information de l'université et tout sous-traitant supplémentaire au sens
du RGPD, sans coût d'hébergement additionnel. Condition : cloisonnement en
conteneur avec ressources plafonnées, pour qu'un entraînement ne dégrade jamais le
LMS en période de partiels.

**Option de repli : un VPS européen conteneurisé**, si la DSI préfère isoler le
service. Kubernetes serait un surdimensionnement ; le serverless sera réévalué si
l'usage devient très irrégulier.

## Architecture cible

```text
SI/LMS -> Caddy HTTPS -> FastAPI -> bundle MLflow @production
                         |    |
                         |    +-> Postgres Bronze/Silver/Gold
                         +------> /metrics -> Prometheus -> Grafana -> canal equipe

APScheduler (drift, decision de reentrainement) -> heartbeat externe (silence detecte)
Drift/performance/labels -> candidat -> gate rappel/AUC/equite -> validation humaine
                                                       |-> promotion ou rollback
```

Dans les deux cas, le traitement et les données restent sous le contrôle de la DSI. Les
conteneurs préservent la portabilité : changer d'hébergeur ne demande pas de
réécrire le service. Caddy fournit le reverse-proxy et renouvelle automatiquement
les certificats HTTPS avec un vrai nom de domaine.

## Coût Run et alternatives

Les montants ci-dessous sont des **ordres de grandeur à confirmer par la DSI**,
pas des devis fournisseurs.

| Option | Ordre de grandeur mensuel | Décision |
|---|---:|---|
| Serveur LMS existant (conteneur cloisonné) | 0 EUR | **Privilégié** : données dans le SI |
| VPS production + sauvegarde + domaine | 10-20 EUR | Repli si isolation souhaitée |
| Petit environnement de test séparé | +5-10 EUR | Recommandé avant production |
| Serverless + base managée | 20-80 EUR | À revoir si trafic très intermittent |
| Kubernetes managé | 60-150 EUR avant services utiles | Écarté à cette échelle |

Le TCO inclut aussi le temps humain : revue mensuelle des alertes, revue annuelle
du modèle, validation DPO et test de restauration des sauvegardes. La haute
disponibilité n'est pas retenue sans SLA : une indisponibilité brève ne met pas
en danger un flux temps réel, car le scoring peut être rejoué.

## Maintenance du modèle

La fréquence de réentraînement suit la disponibilité réelle des résultats de
cohorte. La politique livrée combine :

- contrôle drift/qualité à chaque batch ;
- investigation immédiate si PSI atteint `alert` ;
- entraînement annuel quand les nouvelles issues sont disponibles ;
- entraînement anticipé uniquement si dérive/performance et labels frais ;
- promotion semi-automatique après non-régression du rappel, AUC >= 0,85,
  écart de rappel entre sous-groupes <= 10 points et validation humaine.

MLflow conserve les versions et les alias `candidate`, `production`,
`archived`. Le rollback repointe `production` vers une version précédente.
Chaque entraînement CLI ou planifié ouvre aussi un run MLflow avec paramètres,
métriques et bundle en artefact dans l'expérience `decrochage-l1-training`.
L'API recharge ensuite l'alias via `POST /admin/reload`, protégé par la clé API.
Chaque version enregistrée référence le `run_id` et l'artefact
`model_bundle/model_bundle.joblib` qui l'a produite. Le serveur MLflow utilise
un backend SQLite isolé de la base métier et est exposé sur le port 5000.

Les requêtes API sont journalisées en JSON avec horodatage UTC, niveau, logger,
`request_id`, route, statut et durée, sans payload étudiant. Docker limite chaque
journal à 10 Mo et conserve cinq fichiers afin de borner l'espace disque.

## Alertes et silence

Le service expose `/metrics`. Le dashboard Grafana provisionné présente la
disponibilité, le débit, les statuts HTTP et la latence p95. Grafana attend cinq
minutes avant d'alerter sur l'indisponibilité ou un taux de 5xx élevé, ce qui
limite la fatigue d'alerte.
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
