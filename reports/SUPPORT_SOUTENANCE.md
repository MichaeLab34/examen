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
| Tests | **59** tests, CI verte | slide 18 ⚠️ *le PPTX actuel affiche encore 52* |
| Budget infra | **10-20 €/mois** (ordre de grandeur) | slide 20 |

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

**Le texte entier fait ~3 840 mots.** Débité vite (150 mots/min) : 25 min — il me
reste de la marge. Débité **posément** (130 mots/min, silences compris) : **29 min**,
soit exactement le temps imparti. Donc : je peux parler lentement, articuler, et
laisser des silences. C'est le bon rythme pour un oral.

Si une slide me paraît courte à l'écran, c'est normal : la slide affiche l'ossature,
c'est **moi** qui porte le contenu. Le texte ci-dessous est ce que la slide ne dit pas.

**Règle en cas de dépassement** : je ne coupe jamais une explication pour tenir la
minute — je débite un peu plus vite et je rattrape sur les scènes marquées ⏩, qui
sont volontairement en dessous de leur budget. Ce qu'on retient d'un oral, c'est une
explication claire, pas un chronomètre respecté à la seconde.

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

> ⏩ **Scène dense** — le texte fait ~1 min 15. Je débite un peu plus vite ici :
> l'explication des leurres est un point fort, je ne la sacrifie pas. Je rattrape
> sur les slides 10, 13 et 16, qui sont plus courtes que leur minute.

**Je dis :**

« Voici les distributions des principaux signaux, séparées par classe : en clair les
étudiants qui poursuivent, en foncé ceux qui décrochent.

On voit nettement que les étudiants qui décrochent sont moins présents en cours, se
connectent moins à la plateforme pédagogique, rendent davantage de devoirs en retard,
et déclarent une motivation plus basse.

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

Le résultat : le boosting n'apporte aucun gain d'AUC significatif face à la
régression logistique.

Mon réflexe de départ était pourtant « sur du tabulaire, XGBoost gagne ». Ici, non.

Et comme je dois pouvoir expliquer à un référent pédagogique pourquoi tel étudiant est
signalé, je retiens la régression logistique : ses coefficients se lisent, ceux d'un
boosting non. J'assume l'arbitrage — l'explicabilité l'emporte sur un gain marginal
et non significatif. »

---

### 🎬 Slide 11 · *7.1 Éco-conception : le coût* — **de 11:00 à 11:45** · 45 s à tenir

**Je dis :**

« Un mot sur la sobriété — parce que je ne voulais pas me contenter de l'affirmer.

J'ai instrumenté l'entraînement : pour chaque modèle, je mesure la durée, l'énergie
consommée et l'empreinte carbone estimée, sur le mix électrique français.

Le résultat est net. Le boosting coûte environ dix fois plus de calcul que la
régression logistique ; la forêt aléatoire, vingt à trente fois. Pour un gain d'AUC
nul, voire négatif.

Autrement dit : le coût par point d'AUC gagné est infini. On paie du calcul et on
n'achète aucune performance.

Ce sont des ordres de grandeur — la mesure dépend de la machine, mais l'écart entre
modèles, lui, est stable. »

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

« Pour l'entraînement, un découpage en trois : train, validation, test. Le train pour
apprendre, la validation pour comparer les modèles et choisir le seuil, le test
uniquement pour l'évaluation finale.

Je le dis explicitement : le test n'a jamais servi à choisir quoi que ce soit. Sinon
il ne mesure plus rien.

Les hyperparamètres sont réglés par validation croisée stratifiée, sur le train
seulement. Et le point rassurant : l'AUC obtenue en validation croisée est équivalente
à celle mesurée sur le test mis de côté. C'est le signe qu'il n'y a pas de
surapprentissage.

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

« Les résultats sur le jeu de test — celui que le modèle n'a jamais vu, et qui n'a
servi à choisir ni les hyperparamètres, ni le seuil.

L'AUC est de 0,949. Au seuil retenu, je détecte 95,9 % des futurs décrocheurs. Sur
cette cohorte de test, douze m'échappent — et c'est la matrice de confusion que vous
voyez à l'écran.

La précision est de 63,5 %. Je l'assume complètement : c'est la conséquence directe
du choix que je viens d'expliquer. Sur cent étudiants que je signale, environ
trente-six vont bien. Ils recevront une proposition d'accompagnement dont ils
n'avaient pas besoin — ce qui est très préférable à un décrocheur qu'on laisse passer,
et ce qui reste soutenable : ce sont des entretiens, pas des sanctions.

Et si la direction estimait que le coût d'une fausse alerte est plus élevé que ce que
j'ai supposé — par exemple parce que les tuteurs saturent — on remonte le seuil et on
inverse l'arbitrage. C'est un paramètre, pas une fatalité. »

---

### 🎬 Slide 16 · *11. Explicabilité & équité* — **de 16:00 à 17:00** · 1 min à tenir

**Je dis :**

« Deux choses sur cette slide.

D'abord l'explicabilité. Ce graphique montre la contribution de chaque variable aux
prédictions. Les facteurs qui pèsent sont ceux sur lesquels on peut agir : la
présence, l'activité sur la plateforme, les rendus, la motivation déclarée. Un
référent peut donc comprendre pourquoi un étudiant est signalé — et surtout, quoi lui
proposer.

Ensuite l'équité, que je vous avais annoncée. J'ai mesuré le rappel du modèle par
sous-groupe : femmes, hommes, boursiers, non-boursiers, établissement d'origine. Les
rappels vont de 0,935 à 0,975, soit un écart maximal de 1,9 point — très en dessous
du seuil d'alerte de dix points que je me suis fixé.

Le modèle ne traite donc pas un groupe moins bien qu'un autre, et je peux le prouver. »

---

### 🎬 Slide 17 · *12. Cible secondaire (régression)* — **de 17:00 à 17:30** · 30 s à tenir

**Je dis :**

« Rapidement, la cible secondaire. J'estime la moyenne finale attendue : un R² de
0,68, avec une erreur moyenne d'environ 2,3 points sur 20.

C'est suffisant pour trier entre un soutien léger et un soutien renforcé. Ce n'est pas
suffisant pour annoncer une note à un étudiant — et je ne le ferai pas.

Et bien sûr, cette variable reste exclue des variables explicatives du modèle de
classification. »

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

Tout le code structurant vit dans un package Python. Le notebook, la ligne de commande
et l'API importent exactement le même nettoyage et le même périmètre de variables.
Trois implémentations « équivalentes » finissent toujours par diverger.

Il y a une API avec un contrat d'entrée-sortie explicite, une commande pour le
traitement par lots, une soixantaine de tests automatisés, une intégration continue,
et une image Docker qui ne tourne pas en root. »

---

### 🎬 Slide 19 · *14. Persistance & médaillon* — **de 18:30 à 19:30** · 1 min à tenir

**Je dis :**

« L'architecture de données suit un découpage en médaillon.

Bronze contient les lignes sources telles quelles, avec les données personnelles. Je
l'assume, et c'est une question qu'on peut me poser : pourquoi garder du brut ? Parce
que c'est la zone de traçabilité et de reprise — celle qui permet de rejouer un
traitement, de corriger une erreur d'ingestion, ou de répondre à une réclamation d'un
étudiant. En contrepartie, elle est d'accès restreint, auditée, et purgée à échéance.

Dès la couche Silver, les identifiants directs sont remplacés par un pseudonyme
calculé par HMAC. Gold porte les variables, les scores et les rapports de dérive —
sans aucun identifiant en clair. Autrement dit, tout ce qui sert à modéliser et à
scorer travaille déjà sur des données pseudonymisées.

Chaque lot porte une date d'expiration, et une commande de purge supprime les lots
échus. Toutes les opérations sont journalisées dans une table d'audit, ce qui me
permet de répondre à la question « qui a fait quoi, quand, sur quelles données ».

La protection est donc dans la plomberie, pas dans une note d'intention. »

---

### 🎬 Slide 20 · *15. Architecture proportionnée* — **de 19:30 à 20:30** · 1 min à tenir

**Je dis :**

« Sur le dimensionnement, j'ai commencé par réfléchir en « architecture idéale », puis
je suis revenu aux chiffres : 5 200 étudiants par an, un scoring par semestre, une API
très peu sollicitée.

Dans ces conditions, Kubernetes n'apporte rien — ce serait un cluster à maintenir et à
payer pour une charge qui tient largement sur une machine.

Je propose donc un serveur européen conteneurisé, avec un reverse-proxy qui gère HTTPS
automatiquement, une base Postgres sauvegardée en dehors de l'hôte, et les secrets
hors du dépôt.

L'ordre de grandeur est de dix à vingt euros par mois, plus un environnement de test.
Ce sont des ordres de grandeur à confirmer avec la DSI, pas un devis.

Et la portabilité vient des conteneurs : si le besoin change, on déplace sans
réécrire. »

---

### 🎬 Slide 21 · *16. Cycle de vie* — **de 20:30 à 21:30** · 1 min à tenir

**Je dis :**

« La politique de réentraînement, maintenant — et c'est un point où j'ai changé
d'avis.

Mon premier réflexe était de réentraîner tous les mois. Ça n'a pas de sens ici : la
vérité terrain, c'est-à-dire le fait qu'un étudiant ait abandonné ou non, n'est connue
qu'une fois la cohorte terminée. Réentraîner mensuellement, ce serait réapprendre sur
des étiquettes qui n'existent pas encore.

La politique retenue : un contrôle à chaque lot, avec un indice de dérive par
variable. Si une dérive est détectée, elle déclenche une investigation sur la collecte
— pas un réentraînement à l'aveugle. Le réentraînement, lui, est annuel, quand les
nouvelles étiquettes arrivent.

Chaque entraînement est tracé. Un modèle candidat ne passe en production que s'il
franchit une barrière chiffrée — AUC, rappel, écart d'équité — et surtout après
validation humaine. En cas de problème, on repointe la version précédente : c'est un
retour arrière en une commande. »

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

« Un mot sur le coût et sur la valeur.

Le coût total, ce n'est pas seulement l'hébergement : c'est aussi les sauvegardes, le
temps de la DSI et du délégué à la protection des données, la revue annuelle du
modèle, les interventions.

Sur la valeur, j'ai fait un choix que j'assume : je n'ai pas converti mon AUC en euros
économisés. Ce serait très vendeur, et complètement infondé. L'AUC mesure la capacité
du modèle à discriminer ; elle ne mesure pas l'effet du tutorat sur un étudiant.

Ce que je propose à la place, c'est la méthode de mesure : un pilote progressif, avec
un groupe témoin, pour estimer l'effet réel du dispositif.

La valeur, c'est le nombre d'étudiants utilement accompagnés multiplié par l'effet
causal de l'accompagnement — et cet effet, seule une expérimentation peut le donner. »

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
| **95 % d'AUC, c'est suspect** | Périmètre verrouillé + réaudit colonne par colonne + **données synthétiques à signal fort** ; à revalider sur données réelles. |
| **Pourquoi pas XGBoost ?** | AUC équivalente, mais moins explicable et **un ordre de grandeur de calcul en plus** — je l'ai mesuré. |
| **Éco-conception ?** | Coût mesuré par modèle, coût par point d'AUC, 6 leviers ; le principal est la **fréquence de réentraînement**. |
| **Pourquoi ce seuil ?** | Minimisation du coût métier sur la **validation** ; FN 5× plus coûteux qu'un FP ; le test reste intact. |
| **Votre modèle discrimine-t-il ?** | Retirer `sexe` ne suffit pas (proxys) → audit par sous-groupes, écart de rappel 1,9 pt, et décision humaine. |
| **Bronze contient des données personnelles ?** | Oui, assumé : zone restreinte de traçabilité et de reprise, purgée ; Silver et Gold sont pseudonymisés. |
| **Et la dérive en production ?** | `drift-report` (PSI), seuils `watch`/`alert`, persistance en Gold ; dérive = investigation. |
| **Pourquoi pas un réentraînement mensuel ?** | Les labels d'abandon arrivent **par cohorte** : réentraîner mensuellement, c'est apprendre sur des étiquettes inexistantes. |
| **Si le modèle se dégrade ?** | Gate chiffrée (AUC, rappel, équité) + approbation humaine + alias MLflow et rollback. |
| **Pourquoi pas Kubernetes ?** | 5 200 étudiants/an, batch rejouable : un VPS conteneurisé est proportionné. |
| **Quel ROI ?** | TCO chiffrable, valeur mesurable **par un pilote causal** ; je n'invente aucun gain à partir de l'AUC. |
| **Un job qui ne tourne plus ?** | Heartbeat externe : c'est l'absence de signal qui déclenche l'alerte. |

**Si je ne sais pas** : « Je ne l'ai pas traité dans ce projet. Voici comment je m'y
prendrais : … » — bien meilleur qu'une improvisation.

---

## ✅ Checklist — 15 minutes avant

- [ ] PPTX ouvert en **mode présentateur**, notes visibles (elles sont dans le fichier)
- [ ] Ce conducteur ouvert à côté, ou imprimé
- [ ] Notebook `decrochage_etudiant.ipynb` ouvert **exécuté**, prêt à montrer §8.3 et §12
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
