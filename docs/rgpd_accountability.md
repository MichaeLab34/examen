# Redevabilité RGPD

Ce document met en regard les exigences du RGPD et les contrôles concrets mis en
place dans le projet. C'est une preuve de certification, pas un substitut à la
validation d'un DPO.

## Classification des données

| Catégorie | Colonnes | Traitement |
|---|---|---|
| Identifiants directs / données personnelles | `student_id`, `id_dossier` | Conservés en clair uniquement dans la couche Bronze à accès restreint, pour la traçabilité ; pseudonymisation HMAC-SHA-256 dès Silver ; exclus des variables du modèle |
| Quasi-identifiants | `age`, `filiere`, `etablissement_origine`, `boursier`, dates | Conservés seulement quand ils servent la modélisation du risque ; surveillés pour l'équité et le risque de réidentification |
| Attributs sensibles ou proxy | `sexe`, `boursier`, `etablissement_origine` | Utilisés uniquement dans un cadre de relecture humaine ; métriques par sous-groupe surveillées |
| Scores de risque | `proba_abandon`, `alerte` | Stockés en Gold avec `batch_id`, fenêtre de rétention et journal d'audit |

## Les sept principes du RGPD

| Principe | Contrôle dans le projet | Preuve |
|---|---|---|
| Licéité, loyauté, transparence | Finalité d'accompagnement pédagogique, pas de sanction, information obligatoire des étudiants avant tout déploiement réel | Notebook §4, fiche modèle, notes du support |
| Limitation des finalités | Usage limité à l'accompagnement du risque de décrochage à mi-S1 | README, usage prévu de la fiche modèle |
| Minimisation des données | Identifiants directs exclus des variables ; données personnelles restreintes en Bronze et pseudonymisées dès Silver | `features.py`, `persistence.py`, tests |
| Exactitude | Nettoyage déterministe et contrôles de couverture de la jointure catalogue | `preprocessing.py`, CLI `check-data` |
| Limitation de la conservation | `expires_at` sur les lots ; `decrochage purge-expired` | `ingestion_batch`, `purge_expired_batches` |
| Intégrité et confidentialité | Option de clé d'API, conteneur non-root, secrets en `.env`, stack Postgres, aucune journalisation de payload | `api.py`, Dockerfile, Compose, modèle de menaces |
| Redevabilité | `privacy_audit_log`, fiche modèle, modèle de menaces, matrice RGPD documentée | `privacy_audit_log`, ce document |

## Pseudonymisation

La persistance en base exige `DECROCHAGE_PSEUDONYMIZATION_SECRET`, parce que les
couches Silver, Gold et prédictions remplacent les identifiants directs par des
pseudonymes HMAC. Le secret HMAC doit être stocké hors de Git et géré comme un
secret de production. Un même étudiant conserve le même pseudonyme d'un lot à
l'autre, ce qui permet le suivi longitudinal sans jamais faire sortir
d'identifiant en clair de la couche Bronze restreinte.

La pseudonymisation n'est pas de l'anonymisation : les données restent des
données personnelles au sens du RGPD, parce que le secret permet un
rapprochement contrôlé. Les exports à la ligne doivent donc rester internes, sauf
étude d'anonymisation distincte.

## Rétention

`DECROCHAGE_RETENTION_DAYS` définit la fenêtre d'accompagnement, fixée par défaut
à 365 jours. Chaque lot d'ingestion reçoit un `expires_at`. La commande ci-dessous
supprime les lots échus ainsi que leurs lignes Bronze/Silver/Gold, en écrivant un
événement d'audit :

```bash
uv run decrochage purge-expired
```

## Liste de contrôle avant tout traitement de données étudiantes réelles

- Valider la base légale avec le DPO ; pour une université publique, documenter
  s'il s'agit d'une mission d'intérêt public plutôt que de l'intérêt légitime.
- Publier la notice d'information aux étudiants : finalité, catégories de
  données, durée de conservation, relecture humaine, droits d'accès, de
  rectification et d'opposition.
- Stocker les secrets dans un coffre géré, pas dans des fichiers `.env`.
- Activer le chiffrement au repos de la plateforme et les accès base par rôle.
- Vérifier la conservation et l'accès aux journaux d'audit au niveau requête ;
  les journaux ne contiennent aucun payload brut.
- Réaliser une AIPD si le DPO l'exige.
- Mener une étude de réidentification / anonymisation avant tout export à la ligne.
