# 🎤 Conducteur de soutenance

**Détection précoce du décrochage étudiant en L1** — Staudt Michael
30 min de présentation + 30 min de questions · 33 slides · budget 28 min 45

> Ce document est **mon** outil, pas un livrable. Il sert à dérouler
> `SUPPORT_SOUTENANCE.pptx` sans me perdre : où j'en suis dans le temps, quoi dire,
> quels chiffres citer, quoi ne pas dire.

---

## ⏱️ Contrôle du temps — mes 5 repères

> ⚠️ **Deux numérotations, ne pas les confondre.** Ici je parle **toujours du numéro
> de slide** — celui du compteur PowerPoint, `n / 33`. Le numéro écrit *sur* la slide
> est celui de la section du plan imposé : la slide **30** porte le titre « 18. TCO ».

Je ne surveille pas 33 slides, je surveille **5 points de passage**. À chacun, ce que
je coupe est **toujours devant moi** — jamais une slide déjà passée.

| À la minute… | je dois être sur la slide… | si je suis en retard, je coupe (en aval) | gain |
|---|---|---|---|
| **6:30** | **6** — *les 3 pièges* | rien à couper si tôt : j'accélère sur 7-8-9, une idée par slide | ~1:00 |
| **12:30** | **12** — *les 6 leviers* | slide **17** (régression) : je la résume en une phrase | 0:30 |
| **15:00** | **14** — *choix du seuil* | slides **24 à 29** (captures) : je ne garde que la **23** | 1:30 |
| **22:15** | **22** — *supervision* | slides **24-29** si pas déjà fait, puis la **30** (TCO) | 1:00 à 2:30 |
| **26:45** | **31** — *arbitrages* | je développe **2 cas** au lieu de 3 et je passe à la **33** | 0:45 |

**Ordre dans lequel je sacrifie** (numéros de slide) :
**24-29** (captures, garder la 23) → **17** (régression) → **30** (TCO) → **19** (médaillon).

**Slides intouchables** : **6** (pièges), **14** (seuil), **15** (résultats),
**31** (arbitrages), **32** (limites), **33** (conclusion).

---

## 🎯 Les 3 messages à faire passer coûte que coûte

Si le jury ne retient que trois choses, ce sont celles-ci. Chaque slide y ramène.

1. **La validité avant la performance.** J'ai identifié deux fuites, je les ai
   verrouillées *dans le code*, et je peux le prouver.
2. **Chaque décision est arbitrée, pas subie.** Le seuil, le modèle, la fréquence de
   réentraînement, l'infrastructure : à chaque fois j'ai écarté le réflexe courant
   pour une raison que je sais défendre.
3. **Le score propose, l'humain décide.** Sur des données étudiantes, c'est une
   position éthique et réglementaire, pas une précaution de langage.

---

## 🔢 Antisèche des chiffres

À citer sans hésiter. Si un chiffre m'échappe, je dis « de l'ordre de » plutôt que d'inventer.

| Sujet | Valeur | Où |
|---|---|---|
| Volume | ~5 200 étudiants · 33 colonnes · 40 doublons retirés | slide 6 |
| Taux d'abandon | **~28 %** (classe minoritaire) | slide 4 |
| Features retenues | **31** après verrouillage anti-fuite | slide 6 |
| AUC test | **0,949** | slide 15 |
| Seuil retenu | **0,30** (et non 0,5) | slide 14 |
| Rappel au seuil | **95,9 %** · précision **63,5 %** | slide 14-15 |
| Coût métier | **FN:FP = 5:1** — hypothèse assumée | slide 14 |
| Équité | écart de rappel **1,9 pt** (alerte à 10 pts) | slide 16 |
| Régression | R² ≈ **0,68**, erreur ≈ **2,3 pts/20** | slide 17 |
| Leurres | écart-type **1,6 à 2,3 pts** → aucun signal | slide 9 |
| Éco-conception | boosting ≈ **×10**, RF ≈ **×20-30**, gain nul | slide 11 |
| Tests | **59** tests, CI verte | slide 18 |
| Budget infra | **0 €** sur le serveur du LMS · sinon **10-20 €/mois** | slide 20 |

---

## 🔤 Antisèche des sigles

Si un membre du jury me demande ce que veut dire un sigle, ou si j'ai un blanc.

| Sigle | Développé | En français |
|---|---|---|
| **TCO** | *Total Cost of Ownership* | coût total de possession — tout ce que la solution coûte sur un an |
| **AUC** | *Area Under the Curve* (courbe ROC) | aire sous la courbe : capacité du modèle à bien classer, entre 0,5 et 1 |
| **ROC** | *Receiver Operating Characteristic* | courbe vrais positifs / faux positifs, à tous les seuils |
| **LMS** | *Learning Management System* | la plateforme pédagogique en ligne (type Moodle) |
| **PSI** | *Population Stability Index* | indice de dérive : mesure l'écart entre la population d'hier et celle d'aujourd'hui |
| **SHAP** | *SHapley Additive exPlanations* | contribution de chaque variable à une prédiction |
| **FN / FP** | faux négatif / faux positif | décrocheur raté / fausse alerte |
| **MAE** | *Mean Absolute Error* | erreur absolue moyenne (ici 2,3 points sur 20) |
| **R²** | coefficient de détermination | part de la variance expliquée (ici 0,68) |
| **HMAC** | *Hash-based Message Authentication Code* | pseudonymisation avec une clé secrète |
| **DPO** | *Data Protection Officer* | délégué à la protection des données |
| **CI** | *Continuous Integration* | intégration continue : tests joués à chaque modification |

---

## ⚠️ Ce que je ne dis pas

- ❌ « Mon modèle détecte les décrocheurs » → ✅ « il **estime une probabilité** qui
  **priorise** un accompagnement ».
- ❌ Traduire l'AUC en euros économisés. Je n'ai aucune donnée sur l'effet du tutorat.
- ❌ « C'est prêt pour la production. » → ✅ « la démarche est solide ; la validité
  reste à confirmer sur données réelles ».
- ❌ Survendre la stack Docker comme une architecture d'entreprise : elle est
  **proportionnée**, c'est justement l'argument.
- ❌ M'excuser de la précision à 63,5 % : c'est un **choix**, pas une faiblesse.

---

## 🎬 Déroulé — le texte à dire

**Comment lire.** `« … »` = ce que je dis, tel quel. *(en italique)* = indication de
jeu, je ne le prononce pas. **➜** = ma phrase d'enchaînement vers la slide suivante.
**de X à Y** = la plage horaire où je dois être sur cette slide ; « n min à tenir » =
le temps que je dois y passer.

**Le texte entier fait ~4150 mots**, soit **28 minutes à un débit normal de
présentation** (~145 mots/min). C'est le rythme à tenir : ni précipité, ni traînant.

Si une slide me paraît courte à l'écran, c'est normal : la slide affiche l'ossature,
c'est **moi** qui porte le contenu. Le texte ci-dessous est ce que la slide ne dit pas.

**Règle en cas de dépassement** : je ne coupe jamais une explication pour tenir la
minute. Je débite un peu plus vite sur les scènes denses et je respire sur les autres.

| | Slides |
|---|---|
| ⏩ **Denses** — j'avance, je ne m'attarde pas | **4, 5, 7, 9, 10, 13, 14, 17, 19, 21, 30** |
| 🫁 **Avec marge** — je ralentis, je laisse des silences | **20, 23 à 29, 33** |

Les denses sont celles où j'explique un mécanisme (les fuites, les proxys, les
leurres, le coût métier) : c'est exactement ce que le jury évalue, je ne le sacrifie
pas au chronomètre.

---

### 🎬 Slide 1 · *page de titre* — **de 0:00 à 0:30** · 30 s à tenir

**Je dis :**

« Bonjour. Michael Staudt. Je vous présente mon dossier de certification
« Concevoir et implémenter une solution d'intelligence artificielle ».

Le sujet : détecter, dès le milieu du premier semestre, les étudiants de première
année en risque de décrochage — pour que l'université puisse les accompagner avant
qu'il ne soit trop tard.

Je vous présente ma démarche pendant une trentaine de minutes, et je garde vos
questions pour la fin. »

*(Poser la voix, ne pas se précipiter. Regarder le jury, pas l'écran.)*

---

### 🎬 Slide 2 · *Fil conducteur* — **de 0:30 à 1:00** · 30 s à tenir

**Je dis :**

« Voici comment je vais procéder. Je commence par le problème métier et les données —
c'est là que tout se joue. J'enchaîne sur l'éthique, la préparation, le choix du
modèle et du seuil, puis les résultats. Je termine par l'industrialisation et les
limites.

Un fil rouge traverse tout : la rigueur anti-fuite et l'explicabilité. Ce sont des
données étudiantes ; pour moi, la validité passe avant la performance. »

*(Balayer la liste d'un geste. Ne lire aucun des huit points — ils sont à l'écran,
le jury sait lire.)*

**➜** « Commençons par le problème. »

---

### 🎬 Slide 3 · *Ma démarche* — **de 1:00 à 2:00** · 1 min à tenir

**Je dis :**

« Avant les résultats, un mot sur ma méthode. J'ai tenu un journal de bord : dix
journées datées, plus un bilan. Chaque décision importante y est écrite au moment où
je la prends, avec sa justification.

Pourquoi je commence par là ? Parce que le premier jour, j'ai lancé un modèle rapide
sur toutes les colonnes, juste pour voir. J'ai obtenu une AUC supérieure à 0,95 dès
le premier essai.

Au lieu d'être satisfait, je me suis méfié : à mi-semestre, on ne prédit pas le
décrochage aussi bien. Soit les données étaient trop faciles, soit je trichais sans
le savoir.

C'est ce doute-là qui a donné le fil rouge de tout le projet. Je ne vous présente pas
un modèle qui marche : je vous présente une suite de décisions que je peux toutes
défendre. »

**➜** « Voyons d'abord le besoin. »

---

### 🎬 Slide 4 · *1. Contexte & problème métier* — **de 2:00 à 3:00** · 1 min à tenir

**Je dis :**

« Une université pluridisciplinaire constate un taux d'abandon élevé en première
année : ici, environ 28 % des étudiants. Plus d'un sur quatre.

Ce n'est pas qu'un indicateur. Pour l'étudiant, c'est une année perdue et souvent un
sentiment d'échec durable. Pour l'établissement, c'est un budget engagé sans résultat.

La direction de la réussite étudiante veut donc agir plus tôt. Aujourd'hui, le
repérage se fait après les partiels — c'est-à-dire quand le décrochage est déjà
engagé, et qu'il devient très difficile de faire revenir quelqu'un.

Et les moyens sont limités : un nombre fini de tuteurs, de créneaux de soutien,
d'aides sociales. Il faut donc choisir qui accompagner en premier.

D'où la question métier : quels étudiants accompagner en priorité, dès le milieu du
premier semestre ?

Et la question d'IA qui en découle : estimer une probabilité de décrochage,
explicable, à partir des seules données disponibles à ce moment-là.

Pourquoi le milieu du semestre ? Parce que c'est le premier moment où on dispose d'un
signal d'engagement exploitable, et qu'il reste assez de temps pour agir.

J'insiste sur cette contrainte de temps : elle conditionne tout le projet. J'y reviens
dans deux slides. »

---

### 🎬 Slide 5 · *2. Objectif IA & cadrage* — **de 3:00 à 4:00** · 1 min à tenir

**Je dis :**

« Il y a deux cibles.

La principale, c'est l'abandon : une variable binaire — l'étudiant interrompt sa
formation, ou non. C'est donc de la classification, et c'est sur elle que porte
l'analyse ROC/AUC.

La secondaire, c'est la moyenne finale, traitée en régression.

Pourquoi la classification comme cible principale, plutôt que de simplement prédire
la note ? Parce que la décision métier est binaire : j'accompagne cet étudiant, ou je
ne l'accompagne pas. Une note prédite ne dit pas où placer la frontière ; elle sert
seulement à calibrer l'intensité de l'aide — soutien léger ou soutien renforcé.

Et la sortie du modèle n'est pas un verdict. C'est une probabilité entre zéro et un,
accompagnée d'une alerte au-delà d'un seuil que je justifierai tout à l'heure. Le
score propose, l'humain décide — j'y reviendrai, c'est un point que je tiens.

Dernier élément de cadrage : j'ai enrichi les données avec le catalogue des
formations, qui apporte notamment le taux de réussite historique de chaque filière.
C'est une information connue avant la rentrée, donc disponible au moment du scoring,
sans aucun risque de fuite. »

**➜** « Venons-en aux données — et aux pièges qu'elles contiennent. »

---

### 🎬 Slide 6 · *3. Les données et les 3 pièges* — **de 4:00 à 6:30** · 2 min 30 à tenir

> ⭐ **La slide la plus importante. Prendre le temps, ralentir le débit.**

**Je dis :**

« C'est la slide la plus importante de ma présentation.

Le jeu de données compte environ 5 200 étudiants et 33 colonnes, volontairement
« sales ». Il contient trois pièges.

**Le premier, c'est une fuite de données.** La colonne « moyenne finale » est un
résultat de fin d'année. Elle est évidemment très corrélée à l'abandon — mais
l'utiliser pour prédire, c'est prédire le passé avec le futur. Je l'ai exclue.

**Le deuxième est plus subtil, et c'est celui qui m'a bloqué : la fuite temporelle.**
Les colonnes « moyenne des partiels du premier semestre » et « nombre d'UE validées »
ont l'air parfaitement légitimes — on est au premier semestre, ce sont des données du
premier semestre. Mais la bonne question n'est pas « est-ce que c'est du S1 » : c'est
« quand cette valeur est-elle consolidée ? ». Et la réponse, c'est en fin de
semestre. Or je score à mi-semestre. En production, ces colonnes seraient vides.

Un modèle qui s'appuie dessus affiche une performance flatteuse en validation, et
devient inutilisable le jour où on le déploie.

**Le troisième, ce sont les leurres.** L'énoncé annonce trois variables sans pouvoir
prédictif : le groupe de TD, la couleur de la carte étudiante, le jour d'inscription.
Je ne me suis pas contenté de les écarter parce que l'énoncé le dit : j'ai vérifié.
J'ai tracé le taux d'abandon pour chaque modalité — il est plat, avec un écart-type de
1,6 à 2,3 points. Je le montre au lieu de l'affirmer, et je vous montrerai le
graphique dans trois slides.

Au total, il me reste 31 variables explicatives.

Et pour ne jamais me tromper à nouveau, ce périmètre n'est pas un commentaire dans le
code : c'est une fonction unique, doublée d'un garde-fou qui fait échouer tout le
pipeline si une colonne interdite s'y glisse. »

**➜** « Ces données sont sensibles — d'où la slide suivante. »

---

### 🎬 Slide 7 · *4. Éthique, RGPD & biais* — **de 6:30 à 8:00** · 1 min 30 à tenir

**Je dis :**

« Trois variables demandent une vigilance particulière : le sexe, le statut boursier,
l'établissement d'origine.

Premier risque : le biais. Et attention — retirer la variable « sexe » du modèle ne
suffit pas à le rendre équitable.

Pourquoi ? Parce que d'autres variables peuvent en tenir lieu sans le dire. Si
certaines filières sont très majoritairement féminines, alors la filière porte déjà
l'information du sexe. Le modèle peut donc traiter différemment des groupes sans
jamais voir la variable qu'on a retirée. C'est ce qu'on appelle une variable proxy.

Autrement dit : se rendre aveugle à un critère ne rend pas équitable, ça rend
seulement incapable de le vérifier. Je préfère donc garder ces variables pour
**auditer** le modèle — et je vous montre le résultat de cet audit dans quelques
minutes.

Deuxième risque : l'effet de marquage. Étiqueter un étudiant « à risque » n'est jamais
neutre — ça peut devenir une prophétie auto-réalisatrice.

Côté RGPD, la finalité est strictement limitée à l'accompagnement : jamais une
sanction, jamais une orientation. Et surtout, aucune décision automatisée. C'est
l'esprit de l'article 22 : le score alimente une équipe pédagogique qui garde la main.

Concrètement, la protection est dans l'architecture. La couche brute reste d'accès
restreint, et dès la couche suivante les identifiants sont pseudonymisés par
HMAC-SHA-256. Le pipeline analytique ne voit jamais un identifiant réel. Et le secret
de pseudonymisation n'est pas dans le dépôt. »

---

### 🎬 Slide 8 · *5. Préparation des données* — **de 8:00 à 9:00** · 1 min à tenir

**Je dis :**

« Le nettoyage est déterministe et reproductible : quarante doublons exacts retirés,
ce qui ramène à 5 200 lignes ; conversion des nombres stockés en texte — vous aviez
des valeurs comme « 14.4 km » ou « 61,4 % » ; des dates dans trois formats
différents, harmonisées ; et les modalités catégorielles normalisées.

Trois points que je tiens à souligner.

D'abord, ce nettoyage vit dans un module, pas dans le notebook : il sera rejoué à
l'identique en production.

Ensuite, les couches : Silver, c'est le nettoyé et pseudonymisé ; Gold, c'est la
source unique qui sert à entraîner et à scorer.

Enfin — et c'est un piège classique — l'imputation des valeurs manquantes n'est pas
dans le nettoyage. Elle est dans la pipeline scikit-learn, donc apprise sur le train
uniquement. Calculer une médiane sur le jeu entier ferait fuiter le test vers
l'entraînement. »

---

### 🎬 Slide 9 · *6. EDA* — **de 9:00 à 10:00** · 1 min à tenir

> ⏩ **La plus dense du déroulé** — ~1 min 35 de texte pour une minute prévue.
> J'avance sans traîner : l'explication des leurres est un point fort, je ne la
> sacrifie pas. Je rattrape sur les slides 16, 20 et 33.

**Je dis :**

« Voici les distributions des principaux signaux, séparées par classe : en clair les
étudiants qui poursuivent, en foncé ceux qui décrochent.

On voit nettement que les étudiants qui décrochent sont moins présents en cours, se
connectent moins au LMS — la plateforme pédagogique de l'établissement —, rendent
davantage de devoirs en retard, et déclarent une motivation plus basse.

Deux remarques. Les courbes se chevauchent : aucun de ces signaux ne suffit à lui
seul, c'est leur combinaison qui porte l'information. Et ce sont des facteurs sur
lesquels une équipe pédagogique peut agir — relancer un étudiant absent, c'est
possible ; changer son lycée d'origine, non.

Passons maintenant à la vérification des trois leurres, que je vous avais annoncée.

Pour chacun, j'ai calculé le taux d'abandon groupe par groupe : une barre par groupe
de TD, une barre par couleur de carte, une barre par jour d'inscription.

Si l'une de ces variables avait le moindre pouvoir prédictif, on verrait des barres
nettement plus hautes que les autres. Or elles sont toutes à la même hauteur, autour
de la ligne rouge — qui marque le taux d'abandon moyen, 28 %.

L'écart entre les groupes est d'environ deux points. C'est l'ordre de grandeur de ce
qu'on obtiendrait en formant les groupes au hasard : autrement dit, il n'y a rien à
lire là-dedans. Je peux donc les exclure — non pas parce que l'énoncé le dit, mais
parce que je l'ai vérifié. »

**➜** « Passons au modèle. »

---

### 🎬 Slide 10 · *7. Choix du modèle* — **de 10:00 à 11:00** · 1 min à tenir

**Je dis :**

« Ma démarche : d'abord une baseline — un classifieur naïf, AUC 0,5 — pour savoir ce
que vaut réellement un score. Puis trois familles comparées sur exactement la même
pipeline : régression logistique, forêt aléatoire, gradient boosting.

Je les compare par l'AUC, parce qu'elle est insensible au seuil et au déséquilibre
des classes — contrairement à l'accuracy, qui serait trompeuse avec 28 % de positifs.

Mon réflexe de départ était « sur du tabulaire, XGBoost gagne ». Ici, non : les trois
modèles se tiennent au millième d'AUC près. Et sur un millier d'étudiants, un écart
aussi petit peut venir du simple hasard de l'échantillon — je ne peux donc pas
affirmer qu'un modèle est meilleur qu'un autre.

Alors je ne paie pas ce millième. Entre deux modèles qui font la même chose, je prends
celui que je peux expliquer.

Avec une régression logistique, je peux dire à un référent : « cet étudiant est
signalé parce que sa présence a chuté et qu'il accumule les retards de rendu ». Avec
un boosting, je ne peux pas — et un référent qui ne comprend pas le signalement ne
s'en servira pas. »

---

### 🎬 Slide 11 · *7.1 Éco-conception : le coût* — **de 11:00 à 11:45** · 45 s à tenir

**Je dis :**

« Un mot sur la sobriété — que je ne voulais pas me contenter d'affirmer. J'ai donc
mesuré, pour chaque modèle, la durée d'entraînement, l'énergie consommée et
l'empreinte carbone estimée.

Le boosting coûte environ dix fois plus de calcul que la régression logistique ; la
forêt aléatoire, vingt à trente fois. Et pour quel gain de performance ? Aucun : leurs
AUC sont équivalentes, voire légèrement inférieures.

La dernière colonne du tableau devrait donner le surcoût de calcul par point d'AUC
gagné. Mais comme il n'y a aucun gain, il n'y a rien à diviser — c'est pour ça qu'elle
affiche le symbole infimi. Autrement dit : je paierais dix à trente fois plus de calcul pour
n'acheter aucune performance. »

*(Si on questionne la mesure elle-même — et c'est une bonne question : « sous Windows,
l'estimation de la consommation CPU est approximative. Ces chiffres servent à comparer
les modèles entre eux dans une même session, pas à publier une empreinte absolue.
L'écart entre modèles, lui, est stable d'une exécution à l'autre. »)*

---

### 🎬 Slide 12 · *7.2 Les 6 leviers* — **de 11:45 à 12:30** · 45 s à tenir

**Je dis :**

« Cela dit, soyons honnête sur les ordres de grandeur : toute cette comparaison a
consommé quelques centièmes de wattheure. Sur 5 200 étudiants, le choix de
l'algorithme ne sauve pas la planète.

Le vrai levier est ailleurs — et il est en tête de ce tableau : la fréquence de
réentraînement. Passer d'un rythme mensuel à un rythme annuel supprime onze
entraînements complets par an. Ça pèse infiniment plus lourd que le choix du modèle.

Et vous remarquerez que quatre de ces six leviers relèvent de l'architecture et de
l'exploitation, pas de la modélisation. Deux d'entre eux — la minimisation des données
et la purge — servent d'ailleurs autant le RGPD que la sobriété. »

**➜** « Revenons à l'entraînement proprement dit. »

---

### 🎬 Slide 13 · *8. Entraînement & validation* — **de 12:30 à 13:30** · 1 min à tenir

**Je dis :**

« Je découpe les données en trois : train, validation, test.

J'entraîne le modèle sur le train. La validation me sert à faire mes choix : comparer
les modèles et fixer le seuil de décision.

Le test, je n'y touche pas avant la fin. Il ne sert qu'à mesurer la performance du
modèle final sur des données jamais vues — c'est mon estimation de ce qu'il donnera en
production.

S'il avait servi à choisir un hyperparamètre ou un seuil, cette estimation serait
optimiste : le modèle aurait été ajusté à ce jeu précis, et le test perdrait sa valeur
de mesure indépendante.

Les hyperparamètres, eux, sont réglés par validation croisée stratifiée à l'intérieur
du train. Et le point rassurant : l'AUC obtenue en validation croisée est équivalente
à celle mesurée sur le test — pas de surapprentissage.

Sur le déséquilibre — 28 % de positifs — j'ai utilisé une pondération des classes
plutôt qu'un sur-échantillonnage type SMOTE, parce que la pondération préserve la
calibration des probabilités, dont j'ai besoin juste après pour choisir le seuil. »

---

### 🎬 Slide 14 · *9. Choix du seuil* — **de 13:30 à 15:00** · 1 min 30 à tenir

> ⭐ **La décision la plus défendable du projet. Ralentir.**

**Je dis :**

« Voici la décision dont je suis le plus satisfait.

J'ai failli laisser le seuil à 0,5, parce que c'est la valeur par défaut. Mais 0,5
pose une hypothèse silencieuse : qu'un faux négatif et un faux positif coûtent la
même chose.

Or ici, ce n'est pas le cas. Un faux négatif, c'est un étudiant en train de décrocher
que personne ne repère : ça peut lui coûter son année. Un faux positif, c'est un
entretien de vingt minutes proposé à quelqu'un qui allait bien.

Ne pas choisir, c'est quand même choisir — et c'était choisir l'égalité des coûts,
qui est fausse.

J'ai donc écrit l'hypothèse noir sur blanc : un faux négatif coûte cinq fois un faux
positif. Je balaie ensuite tous les seuils possibles et je retiens celui qui minimise
le coût total — calculé sur la validation, jamais sur le test.

L'optimum tombe autour de 0,30.

Et je l'assume : ce ratio de cinq pour un est une hypothèse métier, pas une vérité.
Elle se rediscute avec la direction, et je peux relancer le calcul avec d'autres
valeurs en une commande. »

---

### 🎬 Slide 15 · *10. Résultats* — **de 15:00 à 16:00** · 1 min à tenir

**Je dis :**

« Voici les résultats sur le jeu de test, mis de côté depuis le début.

L'AUC est de 0,949. Au seuil retenu, je détecte 95,9 % des futurs décrocheurs. Sur
cette cohorte de test, douze m'échappent — et c'est la matrice de confusion que vous
voyez à l'écran.

La précision est de 63,5 %. Je l'assume complètement : c'est la conséquence directe
du choix que je viens d'expliquer. Sur cent étudiants que je signale, environ
trente-six vont bien. Ils recevront une proposition d'accompagnement dont ils
n'avaient pas besoin — c'est très préférable à un décrocheur qu'on laisse passer. Et
pour eux, la conséquence est légère : on leur propose un entretien, on ne les
sanctionne pas.

Et si les équipes pédagogiques estimaient que le coût d'une fausse alerte est plus
élevé que ce que j'ai supposé — parce que les tuteurs saturent, par exemple — on
remonte le seuil et on inverse l'arbitrage. C'est un paramètre, pas une fatalité. »

---

### 🎬 Slide 16 · *11. Explicabilité & équité* — **de 16:00 à 17:00** · 1 min à tenir

**Je dis :**

« Deux choses sur cette slide.

D'abord l'explicabilité. Ce graphique est un summary plot SHAP : il donne la
contribution de chaque variable à la prédiction, et son sens. Les facteurs qui pèsent
le plus sont ceux sur lesquels on peut agir : le taux de présence, l'activité sur le
LMS, les retards de rendu, la motivation déclarée. Un référent peut donc comprendre pourquoi un
étudiant est signalé — et surtout, quoi lui proposer.

Ensuite l'équité, que je vous avais annoncée. J'ai mesuré le rappel du modèle par
sous-groupe : femmes, hommes, boursiers, non-boursiers, établissement d'origine. Les
rappels vont de 0,935 à 0,975, soit un écart maximal de 1,9 point — très en dessous
du seuil d'alerte de dix points que je me suis fixé.

Le modèle ne traite donc pas un groupe moins bien qu'un autre, et le tableau détaillé
par sous-groupe figure dans le notebook. »

*(La preuve est en §12.4 : effectif, taux d'abandon réel, taux d'alerte et rappel par
groupe, avec l'écart maximal calculé à 0,019. À ouvrir pendant les questions si on
demande le détail — pas maintenant.)*

---

### 🎬 Slide 17 · *12. Cible secondaire (régression)* — **de 17:00 à 17:30** · 30 s à tenir

**Je dis :**

« La cible secondaire, demandée par l'énoncé : la moyenne finale.

Attention à ne pas confondre avec ce que j'ai dit tout à l'heure. Je l'ai exclue des
variables **explicatives**, parce qu'elle constituait une fuite pour prédire l'abandon.
Ici, elle n'est pas en entrée : elle est en **sortie**. C'est un second modèle,
entraîné sur les mêmes 31 variables disponibles à mi-semestre, qui la prédit.

R² de 0,68, erreur moyenne d'environ 2,3 points sur 20. De quoi calibrer l'intensité
de l'accompagnement — soutien léger ou renforcé. Pas de quoi annoncer une note à un
étudiant, et je ne le ferai pas. »

**➜** « Passons maintenant à la mise en exploitation. »

---

### 🎬 Slide 18 · *13. Implémentation & service* — **de 17:30 à 18:30** · 1 min à tenir

**Je dis :**

« Le modèle est sérialisé dans un bundle auto-suffisant : la pipeline complète de
pré-traitement, la liste ordonnée des variables, le seuil retenu, et même le catalogue
des formations.

Ce dernier point est volontaire : sans lui, le scoring dépendrait d'un fichier externe
qui pourrait avoir changé depuis l'entraînement — et le modèle appliquerait alors des
taux de réussite différents de ceux qu'il a appris.

Tout le code structurant vit dans un package Python : le nettoyage, le périmètre de
variables, l'entraînement, le scoring.

Trois surfaces l'utilisent — le notebook pour la démonstration, une CLI pour le
traitement par lots, une API FastAPI avec un contrat d'entrée-sortie explicite pour le
scoring à la demande. Les trois importent le même code : je n'ai pas trois versions du
nettoyage qui finiraient par diverger.

Autour : 59 tests automatisés, une intégration continue, et une image Docker qui ne
tourne pas en root. »

---

### 🎬 Slide 19 · *14. Persistance & médaillon* — **de 18:30 à 19:30** · 1 min à tenir

**Je dis :**

« L'architecture de données suit un découpage en médaillon.

Bronze contient les lignes sources telles quelles, avec les données personnelles.
Pourquoi garder du brut ? Parce que c'est la zone de traçabilité et de reprise :
rejouer un traitement, corriger une erreur d'ingestion, répondre à la réclamation d'un
étudiant. En contrepartie, elle est d'accès restreint et auditée.

Dès la couche Silver, les identifiants directs sont remplacés par un pseudonyme
calculé par HMAC. Gold porte les variables, les scores et les rapports de dérive —
sans aucun identifiant en clair. Autrement dit, l'entraînement comme le scoring se
font sur des données déjà pseudonymisées.

Concrètement, la rétention fonctionne comme ceci : chaque lot d'ingestion reçoit une
date d'expiration — un an par défaut, c'est configurable. La commande `purge-expired`
récupère les lots échus, supprime en cascade tout ce qui s'y rattache — de Bronze
jusqu'aux prédictions — puis journalise l'opération. En production, cette commande
serait planifiée ; aujourd'hui, mon ordonnanceur ne pilote que le contrôle de dérive
et le réentraînement.

Et toutes les opérations sensibles sont tracées dans une table d'audit : qui a fait
quoi, quand, sur quelles données.

La protection est donc dans la plomberie, pas dans une note d'intention. »

---

### 🎬 Slide 20 · *15. Architecture proportionnée* — **de 19:30 à 20:30** · 1 min à tenir

**Je dis :**

« Sur le dimensionnement, j'ai commencé par réfléchir en « architecture idéale », puis
je suis revenu aux chiffres : 5 200 étudiants par an, un scoring par semestre, une API
très peu sollicitée. Kubernetes n'apporte rien ici — ce serait un cluster à maintenir
et à payer pour une charge qui tient largement sur une machine.

Deux options, donc. Un serveur européen loué, pour dix à vingt euros par mois. Ou,
plus intéressant : l'université dispose déjà d'un serveur, celui qui héberge le LMS.
Les données d'engagement en viennent — elles ne sortiraient donc jamais du système
d'information de l'établissement. Pas d'hébergeur tiers, pas de sous-traitant
supplémentaire à encadrer au sens du RGPD, et pas de coût d'hébergement.

La condition, c'est le cloisonnement : le scoring tourne dans son propre conteneur,
avec des ressources plafonnées, pour qu'un entraînement ne vienne jamais dégrader le
LMS en pleine période de partiels.

Et c'est précisément ce que la conteneurisation apporte : la même image tourne chez un
hébergeur ou sur le serveur de l'université. Le choix se tranche avec la DSI. »

---

### 🎬 Slide 21 · *16. Cycle de vie* — **de 20:30 à 21:30** · 1 min à tenir

**Je dis :**

« La politique de réentraînement.

Mon premier réflexe était de réentraîner tous les mois. Ça n'a pas de sens ici : la
vérité terrain — savoir si un étudiant a abandonné — n'arrive qu'une fois la cohorte
terminée. Réentraîner mensuellement, ce serait réapprendre sur des étiquettes qui
n'existent pas encore.

Alors pourquoi surveiller la dérive à chaque lot, si le réentraînement est annuel ?
Parce qu'entre deux entraînements, le modèle continue de scorer — et que je ne peux
pas mesurer sa performance réelle, faute de labels. Le PSI des variables d'entrée est
mon seul indicateur disponible.

Il me sert à deux choses. Détecter une rupture de collecte : une variable qui cesse
d'être alimentée, une échelle qui change après une mise à jour du LMS. Et voir si la
population a trop changé pour que le modèle reste valide — auquel cas je suspends
l'usage plutôt que d'alerter à tort.

Le calendrier annuel est donc un filet de sécurité, pas le seul déclencheur : si la
dérive alerte **et** que des labels frais existent, on entraîne un candidat plus tôt.

Ce candidat ne passe en production qu'après une gate chiffrée — AUC, rappel, écart
d'équité — et une validation humaine. Sinon, rollback : l'alias `production` repointe
la version précédente. »

---

### 🎬 Slide 22 · *17. Supervision et alertes* — **de 21:30 à 22:15** · 45 s à tenir

**Je dis :**

« Côté supervision, l'essentiel tient en un principe.

On surveille classiquement l'indisponibilité et les erreurs, mais avec une
temporisation : une alerte ne part que si le problème persiste cinq minutes, et une
dérive ne réalerte pas pendant vingt-quatre heures. Sinon l'équipe se désabonne au
bout de deux jours.

Et le point que je trouve le plus important : un traitement planifié qui ne démarre
plus n'émet aucune erreur. Son silence ressemble exactement au bon fonctionnement.
J'ai donc mis en place un signal de vie : le traitement dit « je suis passé », et
c'est l'absence de ce signal qui déclenche l'alerte. »

**➜** « Et tout cela tourne réellement — je vous le montre. »

---

### 🎬 Slides 23 à 29 · *17.1 à 17.7 — les captures* — **de 22:15 à 24:15** · 2 min à tenir

*(Faire défiler d'un trait, une phrase par capture, sans s'arrêter. Deux minutes pour
sept slides, soit ~15 s chacune en comptant le temps de les afficher : le texte
ci-dessous est volontairement court, la marge sert aux manipulations. Si je suis en
avance, je développe un peu le registre et le rollback — c'est le plus parlant.)*

**Je dis :**

« Le tableau de bord : disponibilité, débit par route, erreurs, latence.

La collecte des métriques, avec la cible de l'API à l'état « up ».

Les deux règles d'alerte, réellement évaluées.

L'API exposée en HTTPS derrière le reverse-proxy.

Le suivi des entraînements, avec leurs paramètres, leurs métriques et les artefacts
produits.

Le registre après un retour arrière : la version 2 avait été promue, puis archivée ;
l'alias de production pointe de nouveau la version 1 — et c'est bien celle que l'API
charge.

Et les journaux applicatifs : une ligne JSON par requête, avec un identifiant de
corrélation, et sans aucune donnée d'étudiant.

Je passe vite volontairement. Le point à retenir : ces preuves-là ne peuvent pas
sortir d'un notebook. Ce sont des processus réseau indépendants, vérifiés dans la
stack conteneurisée. »

---

### 🎬 Slide 30 · *18. TCO & valeur du pilote* — **de 24:15 à 25:15** · 1 min à tenir

**Je dis :**

« TCO, pour *Total Cost of Ownership* — le coût total de possession : tout ce que la
solution coûte sur un an, pas seulement le serveur. L'hébergement, les sauvegardes, le temps que la DSI y
passe, celui du délégué à la protection des données, la revue annuelle du modèle.
Ça, c'est chiffrable — et c'est modeste.

Le gain, lui, je ne peux pas le chiffrer, et je ne vais pas faire semblant. Dire
« mon modèle a 0,95 d'AUC, donc l'université économise tant » serait malhonnête :
l'AUC mesure la capacité du modèle à classer les étudiants, elle ne dit rien de
l'efficacité du tutorat. Le modèle repère ; c'est l'accompagnement qui sauve — ou pas.

Ce que je propose à la place, c'est la méthode pour le mesurer. Un pilote sur une
promotion : je signale tous les étudiants à risque, on en accompagne une partie tirée
au sort, et on compare le taux d'abandon des deux groupes en fin d'année. L'écart
entre les deux, c'est l'effet réel du dispositif — et lui, il se mesure.

Multiplié par le nombre d'étudiants qu'on peut réellement accompagner, ça donne la
valeur du dispositif : un chiffre fondé sur une mesure, pas sur une hypothèse. »

*(Si on objecte l'éthique du groupe témoin : « on ne retire rien à personne —
aujourd'hui, aucun de ces étudiants n'est repéré. Le pilote élargit l'accompagnement à
une partie d'entre eux. Et la capacité de tutorat étant limitée, il faut de toute
façon choisir qui accompagner. »)*

---

### 🎬 Slide 31 · *19. Les arbitrages* — **de 25:15 à 26:45** · 1 min 30 à tenir

> ⭐ **La slide qui répond à « le raisonnement compte autant que le résultat ».**

**Je dis :**

« Cette slide résume ma démarche mieux que les autres : ce sont les décisions que j'ai
failli prendre, et pourquoi je ne les ai pas prises.

J'ai failli garder les moyennes de partiels, parce que « c'est du premier semestre » —
elles sont consolidées en fin de semestre, elles auraient été vides au moment du
scoring.

J'ai failli imputer les valeurs manquantes avant le découpage — ça aurait fait fuiter
le test vers l'entraînement.

J'ai failli prendre XGBoost par réflexe — aucun gain significatif, et un modèle
illisible pour un référent.

J'ai failli laisser le seuil à 0,5 — ça revenait à dire qu'un décrocheur raté coûte
autant qu'une fausse alerte.

Et j'ai failli réentraîner tous les mois, traduire l'AUC en euros, et déployer sur
Kubernetes.

À chaque fois, le réflexe courant aurait donné un chiffre plus flatteur, ou une
architecture plus impressionnante. Et à chaque fois, un dispositif moins valide.

Ces arbitrages sont datés et justifiés dans mon journal de bord. »

*(Si je suis en retard : n'en développer que deux ou trois et laisser le tableau
parler pour le reste.)*

---

### 🎬 Slide 32 · *20. Limites & recommandations* — **de 26:45 à 27:45** · 1 min à tenir

**Je dis :**

« Les limites, maintenant — parce qu'il y en a.

La première est la plus importante : ces données sont synthétiques. Une AUC de 0,95
sur des données synthétiques ne préjuge pas de la performance sur des données réelles.
Avant tout déploiement, il faut revalider sur des données authentiques.

La deuxième : corrélation n'est pas causalité. Mon modèle repère des étudiants à
risque ; il ne démontre pas que l'accompagnement les sauvera. Seul un test comparatif
le dirait.

Pour un vrai passage en production, il resterait à impliquer le délégué à la
protection des données, conduire une analyse d'impact, mettre en place une gestion
fine des droits en base, un coffre à secrets — et surveiller l'équité en continu, pas
une fois.

Et le principe qui ne change pas : le score priorise, il ne décide pas. »

---

### 🎬 Slide 33 · *21. Conclusion* — **de 27:45 à 28:45** · 1 min à tenir

**Je dis :**

« Pour conclure, cinq points.

J'ai neutralisé trois pièges méthodologiques, et je les ai verrouillés dans le code
plutôt que dans un commentaire.

J'ai retenu un modèle explicable et performant — et j'ai mesuré ce qu'il coûte.

J'ai calibré le seuil de décision sur un coût métier explicite, pas sur une valeur par
défaut.

J'ai livré une chaîne d'exploitation vérifiable, dimensionnée pour le besoin réel.

Et j'ai traité le RGPD dans l'architecture, dès la première ligne de persistance.

Au-delà de la technique, ce que j'espère avoir montré, c'est une aide concrète pour
repérer à temps des étudiants en difficulté — en gardant l'humain à la décision.

Le code, les tests et la documentation sont sur le dépôt affiché à l'écran.

Je vous remercie. Je suis à votre disposition pour vos questions. »

*(Marquer un silence. Ne pas enchaîner nerveusement.)*

---

## 💬 Questions du jury — réponses prêtes

Le livrable ne contient **pas** de slides de backup : ce tableau est mon seul filet.
L'avoir sous les yeux pendant les 30 min de questions.

| Question | Ma réponse en une phrase |
|---|---|
| **Il n'y a pas une fuite ?** | Trois pièges traités, périmètre codé dans `features.py`, garde-fou `assert_no_leakage` qui fait échouer le pipeline. |
| **Qu'appelez-vous LMS ?** | Le *Learning Management System* — la plateforme pédagogique en ligne (type Moodle) : cours, dépôts de devoirs, forum. J'en tire les connexions sur 30 jours et les heures cumulées. |
| **95 % d'AUC, c'est suspect** | Périmètre verrouillé + réaudit colonne par colonne + **données synthétiques à signal fort** ; à revalider sur données réelles. |
| **Pourquoi pas XGBoost ?** | AUC équivalente, mais moins explicable et **un ordre de grandeur de calcul en plus** — je l'ai mesuré. |
| **Éco-conception ?** | Coût mesuré par modèle, coût par point d'AUC, 6 leviers ; le principal est la **fréquence de réentraînement**. |
| **Pourquoi prédire `moyenne_finale` si vous l'avez exclue ?** | Exclue comme variable **explicative** (c'était la fuite), pas comme **cible**. Le modèle de régression la prédit à partir des mêmes 31 variables de mi-semestre : elle est en sortie, jamais en entrée. |
| **Pourquoi ce seuil ?** | Minimisation du coût métier sur la **validation** ; FN 5× plus coûteux qu'un FP ; le test reste intact. |
| **Votre modèle discrimine-t-il ?** | Retirer `sexe` ne suffit pas (proxys) → audit par sous-groupes, écart de rappel 1,9 pt, et décision humaine. **Tableau complet : notebook §12.4.** |
| **Comment se fait la purge, concrètement ?** | Chaque lot porte un `expires_at` (rétention configurable, 365 j par défaut). `decrochage purge-expired` sélectionne les lots échus, supprime en cascade Bronze/Silver/Gold/prédictions/rapports, et écrit une entrée `retention_purge` dans le journal d'audit. À planifier en production — le scheduler actuel ne gère que dérive et réentraînement. |
| **Bronze contient des données personnelles ?** | Oui, assumé : zone restreinte de traçabilité et de reprise, purgée ; Silver et Gold sont pseudonymisés. |
| **Et la dérive en production ?** | `drift-report` (PSI), seuils `watch`/`alert`, persistance en Gold ; dérive = investigation. |
| **Pourquoi surveiller la dérive si vous réentraînez annuellement ?** | Parce que je score entre deux entraînements sans pouvoir mesurer la performance (pas de labels). Le PSI est le seul signal disponible : il détecte une rupture de collecte et me dit si la population reste celle du modèle. Et si la dérive alerte **et** que des labels frais existent, `decide_retraining` autorise un candidat anticipé — l'annuel est un filet, pas le seul déclencheur. |
| **Pourquoi pas un réentraînement mensuel ?** | Les labels d'abandon arrivent **par cohorte** : réentraîner mensuellement, c'est apprendre sur des étiquettes inexistantes. |
| **Si le modèle se dégrade ?** | Gate chiffrée (AUC, rappel, équité) + approbation humaine + alias MLflow et rollback. |
| **Pourquoi pas Kubernetes ?** | 5 200 étudiants/an, batch rejouable : une seule machine suffit. |
| **Où hébergeriez-vous la solution ?** | De préférence sur le serveur qui héberge déjà le LMS : les données ne sortent pas du SI, pas de sous-traitant supplémentaire, pas de coût d'hébergement. Condition : cloisonnement en conteneur avec ressources plafonnées, pour ne pas dégrader le LMS. Le VPS reste l'option de repli. |
| **Que recouvre le TCO ?** | *Total Cost of Ownership*, le coût total de possession sur un an : hébergement, sauvegardes, temps DSI et DPO, revue annuelle du modèle, interventions. Pas seulement le serveur. |
| **Quel ROI ?** | Le coût est chiffrable ; le gain, non — l'AUC ne mesure pas l'effet du tutorat. Méthode proposée : un pilote où une partie des étudiants signalés est accompagnée (tirage au sort), et comparaison des taux d'abandon en fin d'année. L'écart mesure l'effet réel. Je n'invente aucun chiffre. |
| **Un job qui ne tourne plus ?** | Heartbeat externe : c'est l'absence de signal qui déclenche l'alerte. |

**Si je ne sais pas** : « Je ne l'ai pas traité dans ce projet. Voici comment je m'y
prendrais : … » — bien meilleur qu'une improvisation.

---

## ✅ Checklist — 15 minutes avant

- [ ] PPTX ouvert en **mode présentateur**, notes visibles (elles sont dans le fichier)
- [ ] Ce conducteur ouvert à côté, ou imprimé
- [ ] Notebook `decrochage_etudiant.ipynb` ouvert **exécuté**, prêt à montrer :
      **§8.3** coût de calcul · **§12.4** tableau d'équité · **§12.2-12.3** SHAP
- [ ] Journal de bord ouvert (on peut me demander une décision datée)
- [ ] Dépôt GitHub ouvert dans un onglet : `github.com/MichaeLab34/examen`
- [ ] Chronomètre lancé au début, repères 6:30 / 15:00 / 22:00 en tête
- [ ] Eau, téléphone en silencieux, notifications coupées

---

## 🔧 Les fichiers et leurs rôles

| Fichier | Rôle |
|---|---|
| `SUPPORT_SOUTENANCE.pptx` | **🏆 LE LIVRABLE remis au jury** — mis en forme hors Marp |
| `soutenance_slides.md` | source Marp : le **contenu** de référence (texte, chiffres, notes) |
| `SUPPORT_SOUTENANCE.md` | ce conducteur |

> ### ⛔ Ne jamais écraser le livrable
>
> `SUPPORT_SOUTENANCE.pptx` n'est **pas** la sortie de Marp : c'est la version
> retravaillée, celle qui part au jury. Une régénération Marp qui écrirait sous ce
> nom **détruirait la mise en forme**. Toujours produire sous un autre nom :
>
> ```powershell
> cd reports
> npx @marp-team/marp-cli soutenance_slides.md --pptx --allow-local-files -o soutenance_slides.pptx
> ```
>
> Puis remettre en forme, et remplacer le livrable **volontairement**.
> Fermer PowerPoint avant toute écriture, sinon le fichier est verrouillé.

**Circuit quand un chiffre ou un texte change** : modifier `soutenance_slides.md` →
régénérer sous `soutenance_slides.pptx` → repasser par l'outil de mise en forme →
remplacer `SUPPORT_SOUTENANCE.pptx` → mettre à jour l'antisèche de ce conducteur.

**État actuel du livrable** : 33 slides (les 2 slides de backup de la source n'y sont
pas — voir la section Questions ci-dessus, qui les remplace), notes orateur présentes
sauf sur 4 slides de captures qui n'en ont pas besoin.

**À savoir sur la source :**

- une slide par bloc séparé par `---` ; les **commentaires HTML deviennent les notes
  orateur** du PPTX — donc rien de technique avant la première slide, ce serait la
  note de la page de titre ;
- le budget temps est le `[m:ss]` en tête de chaque note ; total actuel **28:45** ;
- les figures viennent de `../artifacts/figures/` (générées par le notebook) et les
  captures de `screenshots/docker/` ;
- les chiffres cités viennent des outputs de `notebooks/decrochage_etudiant.ipynb` :
  toute réexécution qui les modifie doit être répercutée dans les slides **et** dans
  l'antisèche ci-dessus.
