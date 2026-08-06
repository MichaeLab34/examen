# Annexe de soutenance — conformité IA & RGPD

## Verdict

Le projet est un **prototype de démonstration**, avec des données synthétiques. Il
montre un score de risque de décrochage destiné à prioriser un accompagnement humain,
mais ne constitue ni une décision automatisée, ni une certification juridique, ni une
preuve de conformité pour un déploiement réel.

## Périmètre du prototype

- Score de risque de décrochage et restitution de facteurs explicatifs.
- Pseudonymisation HMAC-SHA-256, minimisation des colonnes exposées et exclusion des
  identifiants directs du scoring.
- Rétention des lots, purge des lots échus et journalisation des consultations et
  exports.
- Contrôle d'accès du portail par rôles et séparation entre restitution et
  ré-identification dans le SI scolarité.
- Usage explicitement limité à l'aide à l'accompagnement humain : aucune sanction,
  exclusion ou orientation automatique.

## Contrôles présents

Le portail rend visibles les limites du modèle, le caractère synthétique des données,
la finalité d'accompagnement et le rôle de l'équipe pédagogique. Il n'emploie ni
reconnaissance émotionnelle, ni biométrie, ni IA générative. Les traces d'audit, la
rétention et les facteurs explicatifs sont consultables dans le périmètre de la
démonstration.

Ces contrôles sont des éléments techniques et documentaires du prototype. Ils ne
valent pas validation juridique du traitement.

## Limites avant usage réel

Les points suivants sont **non livrés** et doivent être traités avant toute donnée
étudiante réelle :

- validation DPO de la base légale et du traitement ; information des étudiants et
  exercice de leurs droits ;
- AIPD, puis analyse de classification AI Act et FRIA éventuelle ;
- données réelles qualifiées, tests de biais complets et validation de l'utilité
  d'accompagnement ;
- sécurité de production : authentification API obligatoire, chiffrement au repos,
  coffre et rotation des secrets ;
- règles de conservation des artefacts et logs, purge contrôlée et procédure incident,
  avec notification sous 72 heures lorsque le RGPD l'impose.

Le passage en production doit être une décision documentée de l'établissement, avec
validation des responsables compétents. La page ne doit pas être présentée comme une
certification juridique.
