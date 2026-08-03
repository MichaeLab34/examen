# Matrice de couverture des compétences C1 → C9

Objectif : rendre explicite ce que le projet démontre et où le jury peut le vérifier, dans le strict périmètre de l'énoncé.

Le livrable officiel reste le notebook unique `notebooks/decrochage_etudiant.ipynb`. Cette matrice sert de preuve de traçabilité et d'aide à l'oral.

## Synthèse rapide

| Compétence | Niveau couvert | Preuves principales | À défendre à l'oral |
|---|---:|---|---|
| C1 — Identifier un jeu de données pertinent | Fort | Notebook §§2-3, EDA leurres §6.4, jointure catalogue | Besoin métier ≠ problème IA ; données disponibles à mi-S1 ; variables pertinentes vs leurres |
| C2 — Risques éthiques, sociétaux et conformité | Fort | Notebook §4, `docs/rgpd_accountability.md`, `docs/threat_model.md`, `persistence.py` | Score d'aide à la décision, pas sanction ; biais indirects possibles ; DPO/AIPD avant réel |
| C3 — Préparer les données | Fort | Notebook §§5-7, `preprocessing.py`, `features.py`, tests | Nettoyage déterministe ; imputation dans pipeline ; verrou anti-fuite |
| C4 — Choisir un modèle | Fort | Notebook §8, courbe ROC/AUC, baseline + familles comparées | Pourquoi AUC ; pourquoi régression logistique plutôt que modèle plus complexe |
| C5 — Entraîner le modèle | Fort | Notebook §9, `training.py`, `tests/test_training.py` | Train/validation/test ; CV sur train ; seuil choisi sur validation, jamais sur test |
| C6 — Implémenter la solution | Fort+ | Notebook §10, `serving.py`, `api.py`, `cli.py`, `Dockerfile`, CI | Bundle joblib complet ; contrat d'entrée/sortie ; API/CLI ; secrets hors Git |
| C7 — Architecture cible & contraintes | Fort+ | Notebook §11, `ARCHITECTURE_PROJET.md`, `compose.yaml` | Ingestion → Bronze/Silver/Gold → scoring → restitution ; contraintes RGPD/coût/adoption |
| C8 — Mesurer performance & impacts | Fort | Notebook §12, figures, audit équité, régression secondaire | AUC/rappel/précision + coût métier ; expliquer compromis FP/FN |
| C9 — Amélioration continue | Fort+ | Notebook §13, `monitoring.py`, `docs/monitoring_plan.md`, persistance des rapports de dérive | PSI, seuils watch/alert, revue labels, champion/challenger, ré-entraînement |

## Détail par compétence

### C1 — Données, besoin métier et cas d'usage

**Attendus de l'énoncé** : reformuler le besoin, justifier les variables, intégrer le catalogue, prévoir des alternatives.

**Couverture dans examen** :
- Problème métier : prioriser l'accompagnement étudiant dès mi-S1.
- Problème IA : probabilité de `abandon` + régression secondaire `moyenne_finale`.
- Données : SI scolarité, engagement LMS, contexte étudiant, catalogue formations.
- Leurres explicitement analysés : `groupe_td`, `couleur_carte_etudiante`, `jour_inscription`.
- Catalogue joint via `filiere` avec couverture vérifiée.

**Phrase orale** : « Je ne pars pas du modèle : je pars du moment de décision, mi-S1. Toute variable indisponible à ce moment est exclue, même si elle améliorerait artificiellement l'AUC. »

### C2 — Éthique, RGPD et biais

**Attendus de l'énoncé** : variables sensibles, RGPD, biais, risque de marquage, garde-fous.

**Couverture dans examen** :
- Variables/proxys à risque : `sexe`, `boursier`, `etablissement_origine`, contexte socio-économique.
- Finalité limitée : accompagnement, pas sanction.
- Décision humaine : le score propose, l'équipe pédagogique décide.
- Bronze brut restreint ; Silver/Gold pseudonymisés HMAC ; rétention et audit `privacy_audit_log`.
- Menaces STRIDE documentées dans `docs/threat_model.md`.

**Phrase orale** : « Retirer une variable sensible ne suffit pas : des proxys peuvent reproduire un biais. C'est pour cela que je prévois un audit par sous-groupes et une validation DPO avant usage réel. »

### C3 — Préparation des données

**Attendus de l'énoncé** : doublons, parsing nombres/dates, manquants, catégories, feature engineering, cycle de vie.

**Couverture dans examen** :
- `preprocessing.clean_raw` supprime les 40 doublons et normalise nombres, dates et catégories.
- `features.add_engineered_features` ajoute des ratios métier disponibles à mi-S1.
- `features.assert_no_leakage` empêche l'entrée des identifiants, cibles et fuites temporelles dans les features.
- Imputation et encodage placés dans `Pipeline` sklearn pour éviter d'apprendre sur validation/test.
- Persistance médaillon : Bronze, Silver, Gold.

**Phrase orale** : « Le nettoyage est déterministe et rejouable ; l'imputation n'est pas faite avant le découpage, elle est apprise dans la pipeline sur le train seulement. »

### C4 — Choix du modèle

**Attendus de l'énoncé** : baseline, plusieurs familles, ROC/AUC, résultat probabiliste, éco-conception.

**Couverture dans examen** :
- Baseline Dummy.
- Comparaison régression logistique / Random Forest / XGBoost, ou solution de repli selon l'environnement.
- Courbes ROC et AUC.
- Choix final : régression logistique, car performance suffisante, explicabilité forte, coût faible.

**Phrase orale** : « Je privilégie le modèle le plus simple qui atteint le niveau de performance attendu, parce que le contexte exige explicabilité et sobriété. »

### C5 — Entraînement

**Attendus de l'énoncé** : train/validation/test, hyperparamètres, feature engineering, déséquilibre, paramètres retenus.

**Couverture dans examen** :
- Découpage stratifié train / validation / test.
- GridSearchCV sur `C` de la régression logistique, uniquement sur train.
- Déséquilibre géré par `class_weight="balanced"`.
- Seuil choisi sur validation par coût métier FN:FP = 5:1.
- Jeu de test réservé au rapport final, jamais utilisé pour choisir.

**Phrase orale** : « Le test ne sert pas à choisir le modèle ni le seuil ; il sert seulement à mesurer ce que la décision déjà prise donne sur données jamais vues. »

### C6 — Implémentation

**Attendus de l'énoncé** : sérialiser modèle + prétraitement, service de prédiction, versionner données/modèle, intégration SI/LMS.

**Couverture dans examen** :
- `ModelBundle` sérialisé par joblib : pipeline, liste des variables, seuil, catalogue, métadonnées.
- `predict_proba_abandon` accepte des données brutes et renvoie `proba_abandon` + `alerte`.
- CLI : qualité, entraînement suivi dans MLflow, scoring, persistance, dérive, registre, rollback et ordonnanceur.
- API FastAPI : `/health`, `/ready`, `/predict`, clé API, limitation de débit et journaux corrélés par `X-Request-ID`.
- Dockerfile non-root et `compose.yaml` Postgres + API.
- Profil Run : Caddy, Prometheus, tableau de bord et alertes Grafana, service APScheduler.
- CI GitHub Actions : ruff, black, tests et construction de l'image Docker de service.
- Portefeuille de preuves : `docs/evidence_portfolio.md` relie RGPD, médaillon, API/CLI, Docker/CI, dérive PSI, fiche modèle / modèle de menaces et matrice C1→C9.

**Phrase orale** : « Le notebook prouve la démarche ; le package prouve que la solution est rejouable hors notebook. »

### C7 — Architecture cible

**Attendus de l'énoncé** : ingestion → features → inférence → restitution, contraintes et acteurs.

**Couverture dans examen** :
- Architecture complète dans `ARCHITECTURE_PROJET.md`.
- Médaillon : Bronze brut restreint, Silver nettoyé/pseudonymisé, Gold prêt pour la modélisation.
- Restitution : score priorisé pour référents/tuteurs.
- Acteurs : scolarité, LMS, réussite étudiante, DSI, DPO, enseignants, data/ML.
- Contraintes : RGPD, adoption, budget d'accompagnement, éco-conception.

**Phrase orale** : « Je ne mets pas directement le CSV dans le modèle : je sépare les responsabilités pour tracer, nettoyer, scorer et auditer. »

### C8 — Mesure performance et impacts

**Attendus de l'énoncé** : métriques techniques + métier, seuil, restitution, cible secondaire.

**Couverture dans examen** :
- AUC, average precision, rappel, précision, F1, matrice de confusion.
- Coût métier : FN plus coûteux qu'un FP ; seuil ≈ 0,30.
- Explicabilité : permutation importance + SHAP.
- Audit équité par sous-groupes sensibles/proxys.
- Régression secondaire de `moyenne_finale` avec métriques adaptées.

**Phrase orale** : « La précision plus faible est assumée : on accepte des alertes en trop pour éviter de manquer des étudiants réellement à risque. »

### C9 — Amélioration continue

**Attendus de l'énoncé** : MLOps, dérive, ré-entraînement, revue des indicateurs, gestion des versions.

**Couverture dans examen** :
- `monitoring.build_drift_report` calcule le PSI par variable numérique.
- Seuils : watch ≥ 0,10 ; alert ≥ 0,25.
- Persistance possible des rapports dans `gold_drift_report`.
- Contrôle de dérive hebdomadaire planifié et revue métier mensuelle des incidents et retours.
- Décision annuelle ou anticipée selon dérive/performance, uniquement avec des labels récents.
- Chaque entraînement est tracé dans MLflow ; le candidat est enregistré sans promotion automatique.
- Promotion humaine, alias `candidate`/`production`/`archived`, rollback et heartbeat externe.

**Phrase orale** : « Le modèle n'est pas livré une fois pour toutes : il est surveillé, revu avec les labels réels et remplacé seulement si un challenger prouve un gain. »

## Limites de périmètre

Ces éléments resteraient disproportionnés ou hors sujet dans le livrable officiel :

- Un orchestrateur distribué : APScheduler couvre le besoin mono-instance ; une plateforme distribuée ne se justifie qu'en cas de montée en charge.
- Anonymisation avancée k-anonymat/l-diversité/t-proximité : à citer comme culture RGPD, mais pas à appliquer sans besoin de publication de données ligne à ligne.
- Deep learning : non pertinent pour ce tabulaire léger ; risque de dégrader l'explicabilité.

## Priorités de soutenance

1. Anti-fuite et périmètre mi-S1.
2. Éthique/RGPD et décision humaine.
3. Choix du modèle explicable plutôt que performance brute.
4. Seuil choisi par coût métier.
5. Industrialisation raisonnable : bundle + CLI/API + médaillon + surveillance.
