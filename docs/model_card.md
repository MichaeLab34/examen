# Fiche modèle (model card)

## Description du modèle

- Projet : détection précoce du risque de décrochage étudiant en L1.
- Tâche principale : classification binaire de `abandon`.
- Tâche secondaire dans le notebook : régression de `moyenne_finale`.
- Famille de modèle : régression logistique régularisée dans une pipeline scikit-learn.
- Artefact produit par le package : `ModelBundle`, qui embarque le pré-traitement,
  la liste des variables, le seuil, le catalogue et les métadonnées.

## Usage prévu

Le modèle aide les équipes pédagogiques à prioriser les contacts humains à mi-S1.
Il doit être utilisé **uniquement comme aide à la décision**. Il ne doit jamais
exclure, sanctionner, orienter ni étiqueter automatiquement un étudiant sans
relecture humaine.

## Usages hors périmètre

- Décisions individuelles automatisées.
- Utilisation hors L1 sans revalidation.
- Utilisation après le S1 si la fenêtre de disponibilité des variables change.
- Utilisation sur des données étudiantes réelles sans revue du DPO ni information
  des parties prenantes.
- Export ou publication de données à la ligne sans étude d'anonymisation.

## Évaluation

Le notebook rapporte l'AUC ROC, la précision, le rappel, le F1, la matrice de
confusion et l'analyse du seuil métier. La procédure d'entraînement du package
choisit le seuil sur les données de validation et réserve les données de test
au rapport final. Les métadonnées d'entraînement enregistrent également l'écart
de rappel maximal observé entre les sous-groupes surveillés `sexe` et `boursier`.

## Cycle de vie du modèle

Chaque entraînement ouvre un run MLflow avec ses paramètres, ses métriques et le
bundle sérialisé en artefact. APScheduler évalue chaque semaine la dérive et la
politique de réentraînement ; la revue annuelle reste un déclencheur parmi la
dérive et la performance. Lorsque des labels récents justifient un entraînement, le
bundle produit entre dans le registre au statut `candidate`. La promotion en
`production` est bloquée sauf si trois conditions sont réunies : l'AUC de test
atteint au moins 0,85 ; le rappel atteint au moins 0,90 et ne régresse pas par
rapport au modèle en production ; l'écart de rappel entre sous-groupes surveillés
ne dépasse pas 10 points. Passer la barrière technique ne suffit pas : un
relecteur humain doit encore approuver le modèle. La version précédente reste accessible pour un
rollback via l'alias `archived`.

## Limites

Les données fournies sont synthétiques et volontairement simplifiées. Les
performances doivent être revalidées sur des cohortes réelles, avec une analyse
par sous-groupes et un test A/B du dispositif d'accompagnement avant tout
déploiement en production.

## Considérations éthiques

Les variables sensibles ou proxy sont `sexe`, `boursier` et
`etablissement_origine`. Surveiller le rappel et le taux d'alerte par
sous-groupe. Garder la décision finale humaine, explicable et réversible. Les
identifiants directs ne sont pas des variables du modèle : ils ne sont conservés
en clair que dans la couche Bronze à accès restreint, et sont pseudonymisés par
HMAC dès Silver.
