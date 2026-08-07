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

## Surface web ajoutée par le portail de restitution

Le portail (`/portal`) ajoute une surface authentifiée, absente d'un déploiement
d'inférence pur. Il est donc **désactivé par défaut**
(`DECROCHAGE_PORTAL_ENABLED=false`) : une intégration SI/LMS n'expose aucune page
web. Quand il est activé, les menaces suivantes s'ajoutent au tableau ci-dessus.

| Menace | Vecteur | Contrôle |
|---|---|---|
| Usurpation | Vol ou rejeu du cookie de session | Cookie signé (`itsdangerous`), `HttpOnly`, `SameSite=Strict`, `Secure` par défaut (opt-out explicite `DECROCHAGE_PORTAL_ALLOW_INSECURE_COOKIE`, réservé au HTTP local — le déduire du schéma perçu le désactiverait silencieusement derrière Caddy, uvicorn ne faisant confiance à `X-Forwarded-Proto` que depuis `forwarded_allow_ips`), durée de vie 8 h ; le rôle et le périmètre sont **relus en base à chaque requête**, si bien que `disabled_at` révoque immédiatement. Une déconnexion, une rotation de mot de passe ou une révocation incrémentent `portal_user.session_epoch`, que le jeton transporte : tous les cookies déjà émis pour ce compte deviennent invalides, sans table de sessions |
| Usurpation | Force brute / bourrage d'identifiants sur `/portal/login` | Verrouillage par identifiant (5 échecs / 15 min, réponse `429`) **et** limiteur de débit du service élargi à cette route (`RATE_LIMITED_PATHS`) ; message d'erreur identique pour un compte inconnu et un mot de passe erroné (pas d'énumération) ; chaque échec est audité |
| Altération | CSRF sur la déconnexion | Jeton anti-CSRF signé, lié à l'identifiant ; `SameSite=Strict` en défense secondaire |
| Altération | Redirection ouverte via le paramètre `next` | Seules les cibles internes commençant par `/portal/` sont acceptées |
| Divulgation | **IDOR** : consultation d'un dossier hors périmètre | Filtrage du périmètre **dans la requête SQL** (jointure `silver_student`), jamais dans le gabarit ; réponse `404` et non `403`, pour qu'une frontière de périmètre ne confirme pas l'existence d'un dossier |
| Divulgation | `gold_prediction.payload_json` contient l'enregistrement d'entrée complet, dont `moyenne_finale` (cible) et des quasi-identifiants | Liste blanche stricte sur `bundle.feature_cols` (`repository.scoring_payload`) ; test de non-régression interdisant tout rendu du payload brut |
| Divulgation | XSS via une valeur de donnée rendue dans une page | Auto-échappement Jinja2, `|safe` interdit et vérifié par test, CSP `default-src 'self'` sans `unsafe-inline`, aucun style ni script en ligne, aucune ressource distante. La CSP est posée **par l'application elle-même** sur chaque réponse HTML, en plus du Caddyfile : un lancement local, une autre terminaison ou un routage modifié ne doit pas pouvoir servir une fiche de risque sans politique. Les réponses JSON de `/predict` et `/health` ne sont pas concernées |
| Divulgation | Exfiltration de masse par export répété | Plafond `DECROCHAGE_PORTAL_EXPORT_MAX_ROWS` (1 000 par défaut), colonnes d'export fermées, chaque export audité avec acteur et volume |
| Répudiation | Consultation non traçable | `privacy_audit_log` alimenté à chaque vue sensible avec l'identifiant de l'agent et un **motif de consultation** choisi dans une liste fermée |
| Élévation de privilèges | Un référent atteint la vue de conformité | Contrôle de rôle route par route, testé exhaustivement (`tests/test_portal_auth.py`) |

Le portail est en **lecture seule** : il ne déclenche aucun scoring et n'écrit
que des événements d'audit. Une compromission ne permet donc ni de produire des
prédictions hors lot, ni de modifier un dossier, ni d'obtenir une identité
étudiante en clair — le portail ne détient aucune table de correspondance.

## Vulnérabilités des dépendances

La chaîne d'approvisionnement est surveillée de deux façons complémentaires :
les alertes de sécurité Dependabot (activées sur le dépôt), et un audit local
reproductible qui ne dépend d'aucun droit GitHub :

```bash
uv export --format requirements-txt --no-emit-project --no-hashes > /tmp/req.txt
uvx pip-audit -r /tmp/req.txt
```

Les mises à jour de **version** des actions GitHub sont suivies par
`.github/dependabot.yml` (écosystème `github-actions`, groupé en une PR
hebdomadaire). Sans cette déclaration, seules les alertes de sécurité Python
étaient traitées, et les versions d'actions dérivaient jusqu'à la dépréciation
de leur runtime — ce qui s'était produit avec `actions/checkout@v4` et
`astral-sh/setup-uv@v5`.

### Vulnérabilité résiduelle acceptée (état au 2026-08-07)

| Champ | Valeur |
|---|---|
| Avis | `PYSEC-2026-3552` · `CVE-2026-69247` · `GHSA-g6cj-pr64-35w5` |
| Paquet | `cryptography` 49.0.0 (dépendance **transitive**) |
| Sévérité | CVSS 4.0 `AV:N/AC:H/AT:P/PR:N/UI:N/VC:H/VI:N/VA:N` — complexité d'attaque élevée, prérequis nécessaires |
| Nature | Oracle de Bleichenbacher lors du déchiffrement PKCS#7 `EnvelopedData` : les erreurs et le temps de réponse de `pkcs7_decrypt_der`, `pkcs7_decrypt_pem` et `pkcs7_decrypt_smime` sont distinguables |
| Version corrigée | 50.0.0 |
| Statut | **Non corrigeable en l'état** |

**Pourquoi la montée est impossible.** MLflow borne cette dépendance :
`mlflow 3.14.0` exige `cryptography>=43.0.0,<49` et `mlflow 3.15.1` — la version
la plus récente — `cryptography>=43.0.0,<50`. Aucune version publiée de MLflow
n'autorise donc 50.0.0. C'est une contrainte amont, pas un choix de ce projet.

**Ce qui a néanmoins été corrigé.** Monter MLflow de 3.14.0 à 3.15.1 a permis de
passer `cryptography` de 48.0.1 à 49.0.0, ce qui ferme deux des trois
vulnérabilités constatées (`PYSEC-2026-3553` et `PYSEC-2026-3554`, corrigées en
49.0.0).

**Pourquoi le risque résiduel est nul dans ce périmètre.** L'avis conditionne
explicitement l'exploitation à « une application qui déchiffre un
`EnvelopedData` fourni par un attaquant et en reflète le résultat ». Ce projet
n'expose aucun chemin de ce type : ni `pkcs7`, ni `enveloped`, ni `smime`, ni
même un `import cryptography` n'apparaissent dans `src/`, `tests/` ou le
notebook. La bibliothèque n'est présente que comme dépendance transitive de
`codecarbon` et de `mlflow`, qui ne l'utilisent pas non plus pour déchiffrer une
entrée fournie par un tiers. Le code vulnérable n'est jamais atteint.

**Condition de lever.** Réexécuter l'audit dès que MLflow relève sa borne à
`cryptography<51`, puis `uv lock --upgrade-package cryptography`. Cette
acceptation est datée et doit être réévaluée à chaque cycle de maintenance : une
vulnérabilité non exploitable aujourd'hui le redeviendrait si le projet
introduisait un déchiffrement PKCS#7.

**Réserve de méthode.** Cette analyse porte sur l'atteignabilité du code
vulnérable, pas sur une revue du code de `cryptography`. Elle vaut pour le
périmètre actuel et sur données synthétiques ; une mise en service réelle exige
la validation d'un expert en sécurité applicative.

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
multi-instances devra remplacer le limiteur en mémoire par un limiteur partagé :
soit porté par le frontal, soit adossé à Redis.

Avant tout traitement de données étudiantes réelles, la DSI doit fournir un
stockage géré des secrets et un chiffrement au repos avec une rotation de clés
documentée. Le DPO doit valider le registre des traitements et l'AIPD. Ces
validations organisationnelles sont des conditions de mise en service, et ce
dépôt ne les présente pas comme acquises.
