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
3. Sans labels récents : enquêter, ne pas réentraîner à l'aveugle.
4. Avec labels récents : entraîner un candidat puis appliquer la barrière rappel/AUC/équité.

## Tâche planifiée silencieuse

1. L'absence de heartbeat déclenche l'alerte externe.
2. Vérifier `docker compose --profile run ps scheduler`, puis ses journaux.
3. Afficher le manifeste avec `decrochage schedule --help` et contrôler les expressions cron.
4. Rejouer avec `decrochage schedule --run-once monitoring` ou `--run-once retraining` ; l'état persistant évite un doublon le même jour.
5. Vérifier le rapport PSI, le run MLflow et, le cas échéant, la nouvelle version `candidate`.
6. Envoyer `decrochage heartbeat` seulement après validation complète de la tâche.

## Limitation de débit ou traçabilité

1. Récupérer `X-Request-ID` dans la réponse et rechercher cet identifiant dans les journaux API.
2. Pour un HTTP 429, respecter `Retry-After` et réduire la fréquence du client.
3. Ne jamais ajouter le payload étudiant ou la clé d'API aux journaux.
4. En déploiement multi-instance, activer un limiteur partagé au niveau du point d'entrée.

## Portail inaccessible

1. Vérifier que `DECROCHAGE_PORTAL_ENABLED=true` : désactivé, `/portal/*` renvoie
   volontairement `404` et l'API d'inférence reste intacte.
2. Un démarrage en échec sur `DECROCHAGE_PORTAL_SECRET is required` est le
   comportement attendu : le portail refuse de tourner sans secret de session.
   Renseigner le secret depuis le coffre, ne jamais improviser une valeur.
3. Vérifier que `decrochage init-db` a bien été exécuté après la mise à jour :
   la table `portal_user` est créée par cette commande.
4. Contrôler la CSP côté Caddy si la page s'affiche sans style : un style ou un
   script en ligne introduit par erreur serait bloqué — c'est le comportement
   voulu, corriger le gabarit et non la CSP.

## Compte portail verrouillé ou compromis

1. Cinq échecs par identifiant dans la fenêtre configurée renvoient `429`.
   Attendre la fin de la fenêtre (`DECROCHAGE_PORTAL_LOGIN_WINDOW_MINUTES`) ;
   le verrou est en mémoire et se vide aussi au redémarrage du service.
2. Vérifier les événements `portal_login_failed` dans `privacy_audit_log`, ou la
   vue `/portal/conformite`, pour distinguer un oubli d'un bourrage d'identifiants.
3. Révoquer immédiatement un compte suspect : `decrochage portal-user-disable
   <identifiant>`. La révocation prend effet à la requête suivante, même si un
   cookie signé valide est encore en circulation (le rôle est relu en base).
4. Rotation du mot de passe : `decrochage portal-user-passwd <identifiant>`
   (saisie masquée). Ne jamais transmettre un mot de passe par messagerie.

## Rotation du secret de session du portail

1. Générer un nouveau secret hors Git et le placer dans le coffre.
2. Mettre à jour `DECROCHAGE_PORTAL_SECRET` puis redémarrer le service.
3. Conséquence attendue : **toutes les sessions en cours sont invalidées** et les
   agents doivent se reconnecter. Prévenir avant, et éviter la fenêtre de scoring.
4. Consigner la rotation ; ce secret ne protège pas de données étudiantes mais
   l'intégrité des sessions d'agents.

## Export refusé pour volume excessif

1. Le message « Affinez les filtres » signale le dépassement de
   `DECROCHAGE_PORTAL_EXPORT_MAX_ROWS` : c'est un garde-fou anti-exfiltration,
   pas une panne.
2. Demander à l'agent de restreindre par filière ou de cocher « alertes seules ».
3. Ne relever le plafond qu'avec l'accord du DPO, et documenter la décision.
