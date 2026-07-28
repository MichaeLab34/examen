# 🎤 Conducteur de soutenance

**Détection précoce du décrochage étudiant en L1** — Staudt Michael
30 min de présentation + 30 min de questions · 33 slides · budget 28 min 45

> Ce document est **mon** outil, pas un livrable. Il sert à dérouler
> `SUPPORT_SOUTENANCE.pptx` sans me perdre : où j'en suis dans le temps, quoi dire,
> quels chiffres citer, quoi ne pas dire.

---

## ⏱️ Contrôle du temps — mes 4 repères

Je ne surveille pas 33 slides, je surveille **4 points de passage**. Si j'y suis, tout va bien.

| À la minute… | je dois être sur… | sinon |
|---|---|---|
| **6:30** | slide 6 — *les 3 pièges* | je suis parti trop lentement, j'accélère sur 4-5 |
| **15:00** | slide 14 — *choix du seuil* | je coupe 17.2 à 17.7 (bloc captures) |
| **22:00** | slide 22 — *supervision* | je saute 18 (TCO) et 20 (limites) au minimum |
| **28:45** | slide 33 — *conclusion* | — |

**Slides sacrifiables sans dommage**, dans cet ordre : 17.2→17.7 (garder seulement
17.1), puis 12 (régression), puis 18 (TCO), puis 14 (médaillon).
**Slides intouchables** : 6 (pièges), 14 (seuil), 19 (arbitrages), 33 (conclusion).

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

## 📖 Déroulé slide par slide

Format : **durée → cumul**. La phrase entre guillemets est celle que je peux dire telle quelle.

### Ouverture — slides 1 à 3 · jusqu'à 2:00

**1. Titre** · 0:30 → 0:30
« Je vous présente une solution d'IA qui détecte, dès le milieu du premier semestre,
les étudiants de L1 en risque de décrochage, pour prioriser l'accompagnement — de
façon explicable et conforme au RGPD. »
Annoncer : 30 minutes, questions à la fin.

**2. Fil conducteur** · 0:30 → 1:00
Ne pas lire les 8 points. « Le fil rouge, c'est la rigueur anti-fuite et
l'explicabilité, parce que ce sont des données étudiantes. »

**3. Ma démarche** · 1:00 → 2:00
Poser la méthode **avant** les résultats. « Je ne présente pas un modèle qui marche,
je présente une suite de décisions que je peux toutes justifier — écrites au fur et
à mesure, pas reconstruites après coup. »
Citer seulement le déclencheur du jour 1 : l'AUC anormalement haute.
→ *Transition* : « Et ça commence par le problème métier. »

### Cadrage — slides 4 à 5 · jusqu'à 4:00

**4. Contexte** · 1:00 → 3:00
Raconter, ne pas réciter. Le point clé : **la contrainte « mi-S1 » conditionne tout**
— elle interdit certaines variables, j'y reviens dans deux slides.

**5. Objectif IA** · 1:00 → 4:00
Pourquoi de la classification et pas seulement une note prédite : **la décision
métier est binaire** (j'accompagne ou non). La régression ne fait que calibrer.
→ *Transition* : « Maintenant, les données — et les pièges qu'elles contiennent. »

### ⭐ Le cœur — slide 6 · jusqu'à 6:30

**6. Les 3 pièges** · 2:30 → 6:30 — **SLIDE LA PLUS IMPORTANTE, prendre le temps**
1. **Fuite de données** : `moyenne_finale` est un résultat de fin de semestre →
   l'utiliser, c'est prédire le passé avec le futur.
2. **Fuite temporelle** : `moyenne_partiels_s1` et `nb_ue_validees_s1` sont
   consolidées **en fin** de S1 → vides au moment du scoring. Performance flatteuse,
   modèle inutilisable.
3. **Leurres** : je ne me contente pas de les retirer, **je prouve** qu'ils n'ont
   pas de signal (écart-type 1,6 à 2,3 pts).
Conclure : « et pour ne jamais me tromper, un garde-fou fait planter le pipeline si
une colonne interdite entre dans le modèle. »
→ *Transition* : « Ces données sont sensibles — d'où la slide suivante. »

### Éthique et préparation — slides 7 à 9 · jusqu'à 10:00

**7. Éthique & RGPD** · 1:30 → 8:00
Très regardé (C2 a un questionnaire séparé). Anticiper la question piège :
« en retirant le sexe, votre modèle est-il non-discriminant ? » → **non**, des proxys
corrélés peuvent réintroduire un biais → d'où l'audit d'équité, slide 16.

**8. Préparation** · 1:00 → 9:00
Trois idées : le nettoyage est dans un **module** (rejoué à l'identique en prod) ;
Silver pseudonymise ; **l'imputation est dans la Pipeline**, pas avant le split.
Donner un exemple concret de valeur sale : « 14.4 km ».

**9. EDA** · 1:00 → 10:00
« Les signaux d'engagement séparent visuellement les deux groupes. » Puis les leurres :
« et voici la preuve qu'ils n'apportent rien. »

### Modèle et sobriété — slides 10 à 12 · jusqu'à 12:30

**10. Choix du modèle** · 1:00 → 11:00
Justifier l'AUC (insensible au seuil et au déséquilibre, contrairement à l'accuracy).
« À performance égale, je choisis le plus explicable et le plus sobre. »

**11. Éco-conception : le coût** · 0:45 → 11:45
« Je l'ai **mesuré** au lieu de l'affirmer. » Le boosting coûte un ordre de grandeur
de plus pour **zéro gain** → coût par point d'AUC infini.
Si on questionne la mesure : sous Windows l'estimation CPU est approximative, elle
sert à **comparer les modèles entre eux**, pas à publier une empreinte absolue.

**12. Les 6 leviers** · 0:45 → 12:30
Le message : le levier le plus fort n'est pas l'algorithme, c'est de **ne pas
recalculer ce qui n'a pas besoin de l'être**. Mensuel → annuel = 11 entraînements
économisés ; changer d'algorithme économise quelques secondes.
Si le jury enchaîne sur le RGPD : les leviers 4 et 6 réduisent **à la fois**
l'empreinte et la surface de données personnelles.

### Entraînement et résultats — slides 13 à 17 · jusqu'à 17:30

**13. Entraînement** · 1:00 → 13:30
Rassurer sur la robustesse : **AUC en validation croisée ≈ AUC sur test** → pas de
surapprentissage. Pondération plutôt que SMOTE : préserve la calibration.
Insister : **le test n'a pas servi à choisir le seuil**.

**14. Choix du seuil** · 1:30 → 15:00 — **⭐ slide qui marque**
Je ne prends pas 0,5 par défaut : 0,5 suppose qu'un faux négatif et un faux positif
coûtent la même chose. Rater un décrocheur peut lui coûter son année ; une fausse
alerte coûte 20 minutes d'entretien. J'écris le coût : **5:1**. Optimum à **0,30**.
Assumer : le ratio 5:1 est une **hypothèse à valider avec la direction**.

**15. Résultats** · 1:00 → 16:00
« Au seuil retenu, je détecte **95,9 %** des futurs décrocheurs. » Assumer la
précision à 63,5 % : mieux vaut quelques accompagnements en trop qu'un décrocheur raté.

**16. Explicabilité & équité** · 1:00 → 17:00
Deux messages : (1) pas une boîte noire — SHAP montre des facteurs **actionnables**
(présence, LMS, rendus) ; (2) équité vérifiée, écart de rappel **1,9 pt**.

**17. Régression** · 0:30 → 17:30
Court. Utile pour **nuancer** (soutien léger vs renforcé), jamais pour prédire une
note exacte, jamais pour prédire l'abandon.

### Industrialisation — slides 18 à 29 · jusqu'à 24:15

**18. Implémentation** · 1:00 → 18:30
« Du notebook au service, puis au Run » : le notebook explique, le package exécute,
le registre maîtrise les versions.

**19. Médaillon** · 1:00 → 19:30
Bronze reste brut **parce que c'est la zone de preuve et de reprise**, mais restreinte.
Silver pseudonymise. Gold est la seule source de modélisation.

**20. Architecture proportionnée** · 1:00 → 20:30
Dimensionner pour le besoin réel. Le trafic est faible et rejouable : **Kubernetes
n'apporte rien ici**. Les montants sont des ordres de grandeur, pas des devis.

**21. Cycle de vie** · 1:00 → 21:30
Un réentraînement mensuel n'a pas de sens : **la vérité terrain arrive après la
cohorte**. La dérive ouvre une **investigation**, pas un entraînement aveugle.

**22. Supervision** · 0:45 → 22:15
Expliquer le *dead-man's switch* : un job qui ne démarre plus n'émet aucune erreur.
Il doit donc dire « je suis passé » ; c'est **l'absence** de signal qui alerte.

**23-29. Bloc des 6 captures** · 2:00 → 24:15
**Les faire défiler d'un trait**, sans commenter chacune. Un seul message :
« ces preuves ne peuvent pas sortir d'un notebook — ce sont des processus réseau,
vérifiés dans la stack Docker. »
Ne détailler que si on me le demande.

### Recul et clôture — slides 30 à 33 · jusqu'à 28:45

**30. TCO & valeur** · 1:00 → 25:15
On ne dispose ni d'un coût officiel du décrochage ni de l'effet causal du tutorat.
La bonne réponse est de **proposer la méthode de mesure**, pas de fabriquer un chiffre.

**31. Les arbitrages** · 1:30 → 26:45 — **⭐ répond à « le raisonnement compte autant que le résultat »**
Ne pas tout lire : développer **deux ou trois** cas (la fuite temporelle, le seuil,
le réentraînement mensuel) et laisser le tableau parler.
« À chaque fois, le réflexe courant aurait donné un chiffre plus flatteur ou une
architecture plus impressionnante — et un dispositif moins valide. »

**32. Limites** · 1:00 → 27:45
Montrer de la lucidité, ne **pas** survendre. « La démarche est solide et
reproductible ; sa validité en production reste à confirmer sur données réelles. »

**33. Conclusion** · 1:00 → 28:45
Résumer les 5 messages en 30 secondes, finir sur la valeur métier : « une aide
concrète pour accompagner à temps les étudiants à risque. »
Donner le lien du dépôt. Enchaîner sur les questions avec assurance.

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
