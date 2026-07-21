---
marp: true
theme: default
paginate: true
title: "Détection précoce du décrochage étudiant — Soutenance"
---

<!--
========================================================================
SUPPORT DE SOUTENANCE — à convertir en PDF ou PPTX.
Format : Marp (https://marp.app).
  - VS Code : extension « Marp for VS Code » → clic droit → Export slide deck → PDF/PPTX.
  - CLI     : npx @marp-team/marp-cli SUPPORT_SOUTENANCE.md --pptx   (ou --pdf)
Chaque slide est séparée par « --- ». Les blocs de commentaires HTML sont les NOTES
ORATEUR (deviennent les notes du présentateur en PPTX ; invisibles à l'écran).
Cible : 30 min de présentation + 30 min de questions. ~19 slides.
Budget temps indiqué par slide (total ≈ 28 min, garde une marge).
Les figures sont dans ../artifacts/figures/ (générées par le notebook).
========================================================================
-->

# Détection précoce du décrochage étudiant en L1

### Concevoir et implémenter une solution d'IA — soutenance de certification

**Staudt Michael** · *21/07/2026* · v1.3
Python 3.13 · scikit-learn · FastAPI · Postgres · MLflow · Prometheus/Grafana · C1→C9

<!--
[0:30] Se présenter, annoncer le sujet en une phrase :
« Je vous présente une solution d'IA qui détecte, dès le milieu du premier
semestre, les étudiants de L1 en risque de décrochage, pour prioriser
l'accompagnement — de façon explicable et conforme au RGPD. »
Annoncer la durée et qu'on prendra les questions à la fin.
-->

---

## Fil conducteur

1. **Problème & cadrage** métier
2. **Données** et les 3 pièges à éviter
3. **Éthique & RGPD**
4. **Préparation** & anti-fuite
5. **Modèle** : choix, entraînement, seuil
6. **Résultats** & explicabilité
7. **Industrialisation & Run** : API, Docker, registre, alertes, rollback
8. **Limites & recommandations**

<!--
[0:30] Donner la carte. Insister : « le fil rouge de ma démarche, c'est la
RIGUEUR anti-fuite et l'EXPLICABILITÉ, parce que ce sont des données
étudiantes sensibles. » Ne pas lire les 8 points un à un.
-->

---

## 1. Contexte & problème métier — C1

- Une université observe un **fort taux d'abandon en L1** (~28 % ici).
- Besoin : **agir tôt** (mi-S1) avec des ressources limitées (tuteurs, aides).
- Aujourd'hui : repérage **trop tardif** (après les partiels).

**Problématique métier** : *quels étudiants accompagner en priorité, dès mi-S1 ?*
**Problématique IA** : *estimer une probabilité de décrochage, explicable, à
partir des seules données disponibles à mi-S1.*

<!--
[2:00] Raconter le problème comme une histoire, pas comme une fiche.
Le point clé à faire passer : la contrainte « MI-S1 » conditionne tout
(elle interdit certaines variables — j'y reviens au slide des pièges).
« Le modèle n'est qu'une aide à la décision : l'humain garde la main. »
-->

---

## 2. Objectif IA & cadrage — C1

Deux cibles, deux usages :

| Cible | Type | Usage |
|---|---|---|
| `abandon` (0/1) | **Classification** (principale) | Prioriser l'accompagnement — ROC/AUC |
| `moyenne_finale` (/20) | **Régression** (secondaire) | Calibrer l'intensité de l'aide |

- Sortie = un **score de risque** + une **alerte** (seuil), pas un verdict.
- Enrichissement : **catalogue des formations** (taux de réussite historique).

<!--
[1:30] Justifier pourquoi c'est de la CLASSIFICATION (décision oui/non
d'accompagner) et pas juste de la régression. La régression est un COMPLÉMENT
pour calibrer l'intensité. Question jury probable : « pourquoi pas prédire
seulement la note ? » → parce que la décision métier est binaire.
-->

---

## 3. Les données et les 3 PIÈGES — C1 / C3

~5 200 étudiants, 33 colonnes, volontairement **« brutes »**.

| Piège | Colonnes | Décision |
|---|---|---|
| **Fuite de données** | `moyenne_finale` | exclue des features |
| **Fuite temporelle** | `moyenne_partiels_s1`, `nb_ue_validees_s1` | hors périmètre mi-S1 |
| **Leurres** | `groupe_td`, `couleur_carte_etudiante`, `jour_inscription` | prouvés inutiles, exclus |

+ exclure identifiants, constantes, texte libre brut.

> 🔒 Périmètre de scoring **codé et verrouillé** + garde-fou `assert_no_leakage`.

<!--
[3:00] SLIDE LA PLUS IMPORTANTE. Prendre le temps.
- Fuite de données : moyenne_finale est un résultat de FIN de semestre,
  corrélé au décrochage → l'utiliser = tricher.
- Fuite temporelle : les résultats consolidés de fin de S1 ne sont PAS
  disponibles à mi-S1 → performance flatteuse mais modèle inutilisable.
- Leurres : je ne me contente pas de les retirer, je PROUVE (EDA) qu'ils
  n'ont pas de signal.
Conclure : « et pour ne jamais me tromper, j'ai un garde-fou qui plante si une
colonne interdite entre dans le modèle. »
-->

---

## 4. Éthique, RGPD & biais — C2

- **Variables sensibles** : `sexe`, `boursier`, origine → risque de **biais**
  (direct et indirect via proxys).
- **Effet de marquage** : étiqueter « à risque » n'est pas neutre.
- **RGPD** : finalité limitée (aide ≠ sanction), information, **décision humaine**
  (pas d'automatisation — art. 22).
- **Protection appliquée (C2)** : Bronze brut restreint, Silver pseudonymisé HMAC,
  Gold sans identifiants directs, rétention/purge et audit `privacy_audit_log`.
- **Secrets hors Git** : `.env` local ignoré, `.env.example` versionné.

**Garde-fous** : explicabilité · audit d'équité par sous-groupes · usage encadré ·
minimisation · pseudonymisation · accountability.

<!--
[2:00] Montrer une vraie conscience éthique — c'est très regardé (C2 a un
questionnaire séparé). Question piège classique : « en retirant le sexe, votre
modèle est-il non-discriminant ? » → NON, des proxys corrélés peuvent réintroduire
un biais → d'où l'audit d'équité que je montre plus loin.
-->

---

## 5. Préparation des données — C3

Chaîne **déterministe** et reproductible :

- **dédoublonnage** (40 doublons → 5 200 lignes) ;
- **nombres en texte** → float : « 61,8 » · « 61.4% » · « 14.4 km » ;
- **dates multi-formats** → parsées ;
- **encodages** harmonisés (`sexe`, `bac_type`, `mention_bac`, `boursier`…).

**Silver** = données nettoyées et pseudonymisées.  
**Gold** = source unique de modélisation : features mi-S1, labels et split.

Le notebook construit `X`, `y_clf` et `y_reg` **uniquement depuis le Gold dataset**.

<!--
[2:00] Insister sur 3 idées défendables :
1. Le nettoyage est dans un MODULE → rejoué à l'identique en production.
2. Silver pseudonymise, Gold sert réellement à entraîner/scorer.
3. On impute DANS la pipeline (pas avant le split) sinon fuite du test.
Montrer 1-2 exemples concrets de valeurs sales (« 14.4 km »).
-->

---

## 6. EDA — facteurs de risque & preuve des leurres — C3

![w:560](../artifacts/figures/eda_signaux.png)

- Décrocheurs = **moins de présence/LMS**, **plus de retards**, motivation basse.
- Leurres : taux d'abandon **plat** entre modalités (écart-type ≈ 2 pts) → **aucun signal**.

<!--
[2:00] Montrer le graphe des densités par classe (présence, LMS, rendus...).
« On voit visuellement que les signaux d'engagement séparent bien les deux
groupes. » Puis mentionner le graphe des leurres (eda_leurres.png) : « et voici
la preuve que les leurres n'apportent rien. » Tu peux mettre eda_leurres.png en
2e image si la place le permet.
-->

---

## 7. Choix du modèle — C4

Démarche : **baseline** → comparer 3 familles, évaluées par **AUC**.

![w:620](../artifacts/figures/roc_comparaison.png)

**Retenu : régression logistique** — meilleure AUC **et** la plus explicable **et**
la plus sobre.

<!--
[2:00] Justifier AUC (insensible au seuil et au déséquilibre, contrairement à
l'accuracy). Montrer les courbes ROC superposées. Le message : « à performance
égale, je choisis le modèle le plus EXPLICABLE et le plus SOBRE — c'est ce
qu'exige le contexte. » Question probable : « pourquoi pas XGBoost ? » → pas de
gain d'AUC ici, et moins explicable.
-->

---

## 8. Entraînement & validation — C5

- **Split stratifié** train / validation / test (test jamais utilisé pour choisir le seuil).
- **Tuning** de la régularisation `C` par validation croisée stratifiée (scoring AUC).
- **Déséquilibre** (~28 %) : `class_weight="balanced"` (pas de sur-échantillonnage agressif).
- **Seuil métier** choisi sur validation, puis évalué sur test hold-out.
- **AUC CV ≈ AUC test** → pas de surapprentissage visible.

<!--
[1:30] Rassurer sur la robustesse : le fait que l'AUC en validation croisée
égale l'AUC sur le test hold-out prouve qu'on ne surapprend pas. Expliquer
pourquoi pondération plutôt que SMOTE : préserve la calibration des probabilités.
Point important : le test final n'a pas servi à choisir le seuil.
-->

---

## 9. Choix du seuil — raisonner en coût métier — C5 / C8

![w:600](../artifacts/figures/seuil_cout.png)

- **Manquer un décrocheur (FN)** coûte plus cher qu'une alerte inutile (FP).
- Ratio **FN:FP = 5:1** (hypothèse métier explicite) → seuil ≈ **0,30** sur validation.
- Résultat test : **rappel 95,9 %** (on rate très peu de décrocheurs), précision **63,5 %**.

<!--
[2:00] C'est un slide qui impressionne : montrer qu'on ne prend pas 0,5 par
défaut mais qu'on OPTIMISE un coût métier sur validation. Assumer que le ratio 5:1 est une
hypothèse à valider avec la direction. Lien direct avec l'objectif : ne pas
laisser des étudiants décrocher.
-->

---

## 10. Résultats — performance — C8

![w:380](../artifacts/figures/confusion.png)

| Indicateur | Valeur |
|---|---|
| AUC (test) | **0,949** |
| Rappel (seuil métier) | **0,96** |
| Précision | 0,64 |

<!--
[1:30] Lire la matrice de confusion : « au seuil retenu, je détecte 96 % des
futurs décrocheurs. » Assumer la précision plus basse (64 %) : c'est un choix —
mieux vaut quelques accompagnements en trop qu'un décrocheur raté. Coût d'un FN
>> coût d'un FP.
-->

---

## 11. Explicabilité & équité — C8 / C2

![w:520](../artifacts/figures/shap_summary.png)

- Facteurs **actionnables** : présence, LMS, rendus, motivation.
- **Audit d'équité** : rappel comparable F/M/boursier (**0,935–0,975**).

<!--
[2:00] Deux messages : (1) le modèle n'est pas une boîte noire — SHAP et
l'importance des variables montrent des facteurs sur lesquels on peut AGIR
(relance, tutorat). (2) J'ai vérifié l'équité entre sous-groupes sensibles :
pas d'écart marqué. Tu peux aussi montrer importance_permutation.png.
-->

---

## 12. Cible secondaire — régression `moyenne_finale` — C8

![w:430](../artifacts/figures/regression.png)

- Estime la moyenne finale attendue → **calibrer l'intensité** de l'aide.
- R² ≈ **0,68**, erreur ≈ 2,3 pts/20.
- Reste **exclue des features** de classification (fuite).

<!--
[1:00] Court. Montrer que la régression est utile pour NUANCER (soutien léger vs
renforcé), sans prétendre prédire une note exacte. Rappeler qu'on ne s'en sert
JAMAIS pour prédire abandon.
-->

---

## 13. Implémentation & service — C6

- **Bundle sérialisé** (joblib) : Pipeline + features + seuil + catalogue + métadonnées.
- Package `decrochage` : `training.py`, `serving.py`, `api.py`, `cli.py`,
  `persistence.py`, `monitoring.py`, `tracking.py`, `scheduler.py`.
- **Contrats industrialisés** : CLI batch, API FastAPI `/predict`, bundle rechargeable hors notebook.
- **Sécurité API** : clé, limite de débit, requêtes corrélées sans journaliser les données.
- **Cycle de vie** : runs MLflow (paramètres, métriques, artefacts), registre + rollback.
- **Observabilité** : `/metrics`, dashboard Grafana provisionné, alertes et heartbeat.
- **Qualité** : 48 tests `pytest`, lint/format, CI GitHub Actions, Dockerfile non-root.
- Documentation : architecture, modèle, menace, monitoring, guide d'industrialisation.

<!--
[1:30] Montrer qu'on va « du notebook au service puis au Run » : le notebook
explique, le package exécute, et le registre permet de maîtriser les versions.
Mentionner train, predict, drift-report, model-register/promote/rollback.
-->

---

## 14. Persistance SQL & architecture médaillon — C7

**Ingestion → Bronze → Silver → Gold → Entraînement/Scoring → API/CLI → Monitoring**

| Couche | Rôle | Données personnelles |
|---|---|---|
| Bronze | lignes sources brutes, traçabilité | restreintes, purgées |
| Silver | nettoyage + normalisation | IDs remplacés par HMAC |
| Gold | features, split, scores, drift | pas d'identifiants directs |

Stack locale production-like : **Postgres via Docker Compose**.  
Fallback dev : SQLite local ignoré par Git.

<!--
[1:30] Faire le lien avec les exigences RGPD (C2/C7) : Bronze reste brut parce que c'est la
zone de preuve et de reprise, mais elle est restreinte. Silver pseudonymise.
Gold est la seule source de modélisation et de scoring. Mentionner la commande :
decrochage medallion-load.
-->

---

## 15. Architecture d'exploitation proportionnée — C7

**~5 200 étudiants/an · batch mi-S1 · API peu sollicitée**

| Choix | Décision adaptée au projet |
|---|---|
| Hébergement | **VPS européen conteneurisé** ; serverless à réévaluer, Kubernetes écarté |
| Sécurité réseau | **Caddy** reverse-proxy + HTTPS automatique |
| Données | Postgres sur le VPS, sauvegarde hors hôte, secrets hors Git |
| Disponibilité | `/health` + `/ready` ; pas de haute disponibilité sans SLA |
| Budget indicatif | **10–20 €/mois**, +5–10 € pour un environnement de test |

La portabilité vient des conteneurs : évoluer plus tard sans réécrire le service.

<!--
[1:30] Présenter le principe d'architecture : dimensionner pour le besoin réel.
Le trafic est faible et rejouable : Kubernetes n'apporte rien aujourd'hui.
Les montants sont des ordres de grandeur à confirmer par la DSI, pas des devis.
-->

---

## 16. Cycle de vie du modèle — C9

1. **Contrôler chaque batch** : qualité + PSI (`watch` ≥ 0,10 ; `alert` ≥ 0,25).
2. **Dérive sans labels frais** : investiguer la collecte, ne pas réentraîner à l'aveugle.
3. **Labels de la nouvelle cohorte disponibles** : entraîner un `candidate` annuel.
4. **Tracer l'expérience** : paramètres, métriques et bundle dans un run MLflow.
5. **Gate** : AUC ≥ 0,85 · rappel ≥ 0,90 sans régression · écart équité ≤ 10 pts.
6. **Validation humaine obligatoire**, puis alias MLflow `production` ou rollback.

APScheduler contrôle puis évalue la politique chaque semaine ; l'échéance
annuelle reste un déclencheur. Un
redémarrage le même jour ne crée pas de doublon.

<!--
[2:00] Dans ce contexte, un réentraînement mensuel
n'a pas de sens car la vérité terrain arrive après la cohorte. Le déclencheur
drift ouvre une investigation ; il n'autorise un entraînement que si les labels
frais existent. Le candidat du notebook passe le gate technique (écart F/M et
boursier = 1,9 pt) mais reste « en attente » sans approbation humaine.
-->

---

## 17. Supervision et alertes — C8 / C9

| Besoin | Réponse |
|---|---|
| Quotidien | canal d'équipe réussite étudiante / DSI |
| Vue Run | dashboard Grafana : disponibilité, débit, statuts HTTP, latence p95 |
| Incident technique | API indisponible ou 5xx > 1 % **pendant 5 min** |
| Tâche silencieuse | heartbeat externe : contrôle drift/réentraînement attendu mais absent |
| Critique | astreinte DSI seulement pendant la fenêtre de scoring |

**Hystérésis + cooldown 24 h** : une dérive persistante ne spamme pas l'équipe.

<!--
[1:30] Expliquer le dead-man's switch : un job qui ne démarre plus n'émet
aucune erreur. Il doit donc envoyer un « je suis passé » ; l'absence du signal
déclenche l'alerte. L'astreinte 24/7 permanente serait disproportionnée ici.
-->

---

## 17.1 Grafana confirme un service disponible

![Dashboard Grafana alimenté par la stack Docker](screenshots/docker/grafana-dashboard.png)

- Disponibilité, débit par route, erreurs 5xx et latence p95 sont visibles en conditions réelles.
- Les mesures proviennent de l'API conteneurisée et de Prometheus, pas de sorties calculées dans le notebook.

---

## 17.2 Prometheus collecte, Grafana alerte

![Cible API active dans Prometheus](screenshots/docker/prometheus-targets.png)

![Règles d'alerte provisionnées dans Grafana](screenshots/docker/grafana-alert-rules.png)

- Prometheus confirme que la cible `decrochage-api` est collectée sur `/metrics` avec l'état `UP`.
- Grafana évalue deux règles provisionnées : indisponibilité de l'API et taux d'erreurs 5xx supérieur à 1 %.

---

## 17.3 Caddy expose l'API en HTTPS

![Documentation Swagger chargée via Caddy en HTTPS](screenshots/docker/caddy-https-api.png)

- Caddy termine HTTPS et transmet les requêtes au conteneur API.
- Le certificat est local pour la démonstration ; un domaine et un certificat gérés seraient requis en production.

> Ces preuves ne peuvent pas être produites par le notebook seul : Caddy, Prometheus et Grafana sont des processus réseau indépendants, exécutés dans la stack Docker et vérifiés depuis un navigateur.

<!--
[1:00] Montrer que le notebook prouve la démarche analytique, tandis que ces
captures prouvent l'exploitation réelle : HTTPS, collecte périodique, dashboard
et évaluation continue des alertes. Les captures ont été réalisées sur la stack
Docker locale avec Playwright.
-->

---

## 18. TCO & valeur du pilote — C7 / C9

- **TCO** = hébergement + sauvegardes + temps DSI/DPO + revue du modèle + interventions.
- Le coût d'infrastructure seul ne mesure pas la valeur du dispositif.
- Formule pilote :
  **étudiants utilement accompagnés × effet causal du dispositif**.
- L'AUC mesure la discrimination du modèle, **pas** l'impact du tutorat.
- Mesure attendue : pilote progressif / A-B test, capacité des tuteurs, faux positifs.

> Aucun gain financier inventé : les hypothèses doivent être validées avec l'université.

<!--
[1:30] Adapter le ROI industriel au contexte éducatif. On ne dispose pas d'un
coût officiel du décrochage ni de l'uplift causal de l'accompagnement. La bonne
réponse est de proposer la méthode de mesure, pas de fabriquer un chiffre.
-->

---

## 19. Limites & recommandations

- **Données synthétiques** → AUC élevée à revalider sur données réelles.
- **Corrélation ≠ causalité** → A/B test nécessaire avant conclusion business.
- **Production réelle** : DPO, DPIA/AIPD, RBAC DB, coffre de secrets, dashboards.
- **Run réel** : confirmer le TCO avec la DSI, brancher le canal d'alerte et tester les sauvegardes.
- **Éthique** : surveiller l'équité en continu, documenter les recours.
- Le score **priorise**, il ne **décide** pas.

<!--
[1:30] Montrer de la lucidité — le jury valorise un candidat qui connaît les
limites de son travail. NE PAS survendre. « Ce que j'ai construit est une
démarche solide et reproductible ; sa validité en production reste à confirmer
sur données réelles. »
-->

---

## 20. Conclusion — du modèle au Run, C1→C9

- **Rigueur anti-fuite** (3 pièges neutralisés + garde-fou).
- **Modèle explicable** performant (AUC 0,95, rappel 95,9 %).
- **Seuil calibré** sur le coût métier.
- **Prototype Run vérifiable** : HTTPS, métriques, alertes, heartbeat, promotion humaine et rollback.
- **RGPD documenté et implémenté** dès la persistance.

**Merci — vos questions ?**

<!--
[1:00] Résumer en 30 s les 5 messages. Terminer par la valeur métier : « une
aide concrète pour accompagner à temps les étudiants à risque. » Enchaîner sur
les questions avec assurance.
-->

---

<!-- _paginate: false -->
## Backup — questions probables du jury

- **Fuites ?** → 3 pièges + `assert_no_leakage` + périmètre codé.
- **AUC 0,95 = fuite ?** → non : verrou + données synthétiques ; à revalider.
- **Pourquoi LogReg et pas XGBoost ?** → même AUC, plus explicable/sobre.
- **Choix du seuil ?** → minimisation du coût métier sur validation (FN >> FP).
- **Équité / RGPD ?** → audit sous-groupes + décision humaine + minimisation.
- **Bronze contient du brut ?** → oui, zone restreinte de traçabilité ; Silver/Gold protègent l'usage.
- **Drift en production ?** → `decrochage drift-report` + Gold SQL + seuils PSI + ré-entraînement.
- **Pourquoi pas mensuel ?** → les labels d'abandon arrivent par cohorte ; drift = investigation, pas entraînement aveugle.
- **Modèle dégradé ?** → gate rappel/AUC/équité, approbation humaine, alias MLflow et rollback.
- **Pourquoi pas Kubernetes ?** → faible volume, batch rejouable ; VPS conteneurisé proportionné.
- **Job qui ne tourne plus ?** → heartbeat externe : l'absence de ping déclenche l'alerte.
- **ROI ?** → TCO chiffré, valeur mesurée par pilote causal ; aucun gain inventé à partir de l'AUC.

<!--
Slide de secours, à ne PAS présenter : à garder sous la main pendant les 30 min
de questions. Prépare 1-2 phrases pour chacune à l'avance.
-->
