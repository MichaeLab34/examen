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
| Comptes d'agents (portail) | `portal_user.username`, `display_name` (facultatif), `role`, `scope_filieres` | Données de **personnels**, non d'étudiants. Finalité : contrôle d'accès. L'identifiant est un identifiant du SI, **jamais une adresse de courriel** (minimisation). Mots de passe hachés en Argon2id. Désactivation par `disabled_at` sans suppression, pour préserver la traçabilité de l'audit |

## Portail de restitution : finalité et garanties

Le portail (`/portal`) matérialise la restitution aux référents, c'est-à-dire le
moment où la décision redevient humaine. Il constitue un traitement distinct, à
déclarer au registre.

| Question | Réponse |
|---|---|
| Finalité | Prioriser un accompagnement pédagogique humain à partir de scores déjà calculés |
| Catégories de personnes | Étudiants (pseudonymisés) et personnels habilités (comptes) |
| Destinataires | Référents pédagogiques, pilotage de la réussite étudiante, DPO — chacun dans son périmètre |
| Base légale à confirmer | Mission d'intérêt public de l'établissement, à valider par le DPO |
| Conservation | Aucune donnée propre : le portail lit les lots existants et suit leur `expires_at` |
| Décision automatisée | **Aucune.** Le portail n'envoie rien, ne convoque personne, ne modifie aucun dossier (art. 22 RGPD) |

**Décision structurante : le portail ne ré-identifie pas.** Il travaille
exclusivement sur les pseudonymes HMAC produits dès Silver, n'accède pas aux
tables Bronze et ne détient aucune table de correspondance. Le rapprochement
`pseudonyme → étudiant` s'opère hors du portail, dans le SI scolarité, à partir
d'un export pseudonymisé à colonnes fermées.

Conséquence assumée : l'ergonomie est moins directe — un référent passe par un
export et un rapprochement côté SI. C'est le prix de la minimisation, et il est
délibéré : une compromission du portail n'expose aucune identité étudiante. La
ré-identification à la demande dans le portail a été écartée ; elle exigerait un
chiffrement applicatif, une gestion de rotation de secret et très probablement
une AIPD dédiée.

**Effectif minimal sur la vue agrégée.** La vue de pilotage ne publie une ligne
par filière qu'au-delà de cinq étudiants scorés (`repository.MIN_GROUP_SIZE`).
En deçà, un « agrégat » désigne des individus : sur une filière d'un seul
inscrit, la médiane *est* son score. Les filières trop petites sont regroupées
sur une ligne unique, et ce regroupement est lui-même retiré s'il reste sous le
seuil. Pour la même raison, la vue publie la médiane et le **décile supérieur**,
jamais le maximum — un maximum est la valeur d'un étudiant précis. C'est
l'application ciblée d'un principe de k-anonymat, là où elle a un sens : une
vue agrégée destinée à un rôle qui n'a pas accès aux dossiers individuels.

**Redevabilité des consultations.** Toute vue sensible et tout export écrivent un
événement dans `privacy_audit_log` avec l'identifiant de l'agent comme `actor`,
un pseudonyme comme `target_id` et un **motif de consultation** choisi dans une
liste fermée. La vue « Conformité », réservée au rôle `auditeur`, restitue ce
journal, les échéances de conservation et la version de modèle en vigueur —
**sans donner accès à aucun score individuel**.

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
