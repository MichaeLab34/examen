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

**Staudt Michael** · *09/07/2026* · v1.1
Python 3.13 · scikit-learn · FastAPI · CLI · notebook + package C1→C9

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
7. **Industrialisation** : CLI, API, Docker, CI, monitoring
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

**Garde-fous** : explicabilité · audit d'équité par sous-groupes · usage encadré ·
minimisation.

<!--
[2:00] Montrer une vraie conscience éthique — c'est très regardé (C2 a un
questionnaire séparé). Question piège classique : « en retirant le sexe, votre
modèle est-il non-discriminant ? » → NON, des proxys corrélés peuvent réintroduire
un biais → d'où l'audit d'équité que je montre plus loin.
-->

---

## 5. Préparation des données — C3

Nettoyage **déterministe** et reproductible (module `preprocessing.py`) :

- **dédoublonnage** (40 doublons → 5 200 lignes) ;
- **nombres en texte** → float : « 61,8 » · « 61.4% » · « 14.4 km » ;
- **dates multi-formats** → parsées ;
- **encodages** harmonisés (`sexe`, `bac_type`, `mention_bac`, `boursier`…).

**Feature engineering** (mi-S1, sans fuite) : taux de rendu, intensité LMS,
`commentaire_present`, ancienneté d'inscription.
**Imputation/encodage DANS la Pipeline** → fit **train seul** (anti-fuite).

<!--
[2:00] Insister sur 2 idées défendables :
1. Le nettoyage est dans un MODULE → rejoué à l'identique en production.
2. On impute DANS la pipeline (pas avant le split) sinon fuite du test.
Montrer 1-2 exemples concrets de valeurs sales (« 14.4 km ») — ça marque.
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
- Package `decrochage` : `training.py`, `serving.py`, `api.py`, `cli.py`, `monitoring.py`.
- **Contrats industrialisés** : CLI batch, API FastAPI `/predict`, bundle rechargeable hors notebook.
- **Qualité** : tests `pytest`, lint/format, CI GitHub Actions, Dockerfile non-root.
- Documentation : architecture, modèle, menace, monitoring, guide d'industrialisation.

<!--
[1:30] Montrer qu'on va « du notebook au service » : le notebook explique la
démarche, le package exécute la chaîne réutilisable. Mentionner les commandes :
decrochage train, predict, serve, drift-report. Le piège évité : classes custom
importables hors __main__, donc bundle rechargeable en API/CLI.
-->

---

## 14. Architecture cible & contraintes — C7

**Ingestion → Préparation anti-fuite → Entraînement/Scoring → API/CLI → Restitution → Monitoring**

| Contrainte | Réponse |
|---|---|
| Technique | batch hebdo + API FastAPI, modèle léger |
| RGPD | décision humaine, minimisation |
| Éco-conception | modèle linéaire sobre |
| Organisationnelle | explicabilité → adoption |
| Exploitation | Docker + CI + tests + rapport PSI |

<!--
[1:30] Dessiner la chaîne à l'oral (ou montrer le schéma ASCII de
docs/architecture.md). Point clé : la DÉCISION HUMAINE est explicitement dans
l'architecture (à la restitution). Citer les acteurs : réussite étudiante, DPO,
DSI, référents.
-->

---

## 15. Amélioration continue (MLOps) — C9

- **Monitoring exécutable** : `decrochage drift-report` calcule le drift PSI.
- **Suivi** : drift, performance (AUC), équité, complétude — avec
  **seuils d'alerte chiffrés**.
- **Ré-entraînement** : annuel (nouvelle promotion) + événementiel (drift).
- **Versioning** : données + modèle + métriques dans le bundle.
- **Gouvernance** : model card, threat model, validation CI avant livraison.
- **A/B test** pour mesurer l'impact **causal** de l'accompagnement.

<!--
[1:30] Montrer qu'on pense au CYCLE DE VIE, pas juste au modèle figé. Insister :
les vraies étiquettes d'abandon arrivent en fin d'année → ré-entraînement annuel
logique. Le A/B test est ce qui permettrait de PROUVER que ça marche vraiment.
-->

---

## 16. Limites & recommandations

- **Données synthétiques** → AUC élevée à revalider sur données réelles.
- **Corrélation ≠ causalité** → A/B test nécessaire avant conclusion business.
- **Éthique** : surveiller l'équité en continu, cadrer avec le DPO.
- Le score **priorise**, il ne **décide** pas.

<!--
[1:30] Montrer de la lucidité — le jury valorise un candidat qui connaît les
limites de son travail. NE PAS survendre. « Ce que j'ai construit est une
démarche solide et reproductible ; sa validité en production reste à confirmer
sur données réelles. »
-->

---

## 17. Conclusion — une démarche C1→C9

- **Rigueur anti-fuite** (3 pièges neutralisés + garde-fou).
- **Modèle explicable** performant (AUC 0,95, rappel 95,9 %).
- **Seuil calibré** sur le coût métier.
- **Industrialisation légère livrée** (CLI + API + Docker + CI + monitoring).
- **Éthique et conforme** by design.

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
- **Drift en production ?** → `decrochage drift-report` + seuils PSI + ré-entraînement.

<!--
Slide de secours, à ne PAS présenter : à garder sous la main pendant les 30 min
de questions. Prépare 1-2 phrases pour chacune à l'avance.
-->
