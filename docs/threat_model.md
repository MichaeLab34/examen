# Modèle de menaces

## Périmètre

La surface exposée est un service FastAPI qui fournit une prédiction de risque de
décrochage à partir de dossiers étudiants bruts. Les données sont sensibles parce
qu'elles contiennent des variables académiques, d'engagement et de contexte
social.

## Principales menaces et contrôles

| Menace | Risque | Contrôle |
|---|---|---|
| Usurpation (*spoofing*) | Appels de prédiction non autorisés | `DECROCHAGE_API_KEY` optionnelle, via l'en-tête `X-API-Key` |
| Altération (*tampering*) | Un payload invalide modifie le comportement du scoring | Validation Pydantic des requêtes et garde-fou sur les variables |
| Répudiation | Aucune trace des opérations de scoring | Journal de requêtes structuré avec `X-Request-ID`, route, statut et durée |
| Divulgation d'information | Données étudiantes fuitées par les journaux | Ne jamais journaliser les payloads ni les clés d'API |
| Divulgation d'information | Identifiants directs stockés en Bronze restreint | RBAC, aucune journalisation de payload, purge de rétention, accès contrôlé par le DPO |
| Divulgation d'information | Identifiants directs propagés aux couches analytiques | Pseudonymisation HMAC-SHA-256 dès Silver |
| Déni de service | Appels de prédiction surdimensionnés ou répétés | Le schéma d'API plafonne les requêtes à 500 enregistrements et applique une limite de débit configurable par client |
| Élévation de privilèges | Impact d'une évasion de conteneur | L'image Docker tourne sous l'utilisateur non-root `appuser` |

## Notes RGPD

- Finalité : accompagnement pédagogique, pas sanction.
- Minimisation : les identifiants sont exclus des variables du modèle, restreints en Bronze et pseudonymisés dès Silver.
- Rétention : les lots portent un `expires_at` ; `decrochage purge-expired` supprime les données échues.
- Relecture humaine : les alertes sont des recommandations pour les équipes d'accompagnement.
- Redevabilité : les actions touchant à la vie privée sont journalisées dans `privacy_audit_log`.

## Conditions à lever avant une mise en production

Les contrôles applicatifs sont exécutables dans le prototype : clé d'API,
corrélation des requêtes sans journalisation des payloads, limite de débit par
client, plafonds de schéma, rétention et pseudonymisation. Un déploiement
multi-instances devra remplacer le limiteur en mémoire par un limiteur partagé,
en bordure ou adossé à Redis.

Avant tout traitement de données étudiantes réelles, la DSI doit fournir un
stockage géré des secrets et un chiffrement au repos avec une rotation de clés
documentée. Le DPO doit valider le registre des traitements et l'AIPD. Ces
validations organisationnelles sont des conditions de mise en service, et ce
dépôt ne les présente pas comme acquises.
