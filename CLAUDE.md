# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Nature du projet

`examen/` est le **cas d'usage de certification** « Concevoir et implémenter une solution d'IA » : détection précoce du **décrochage étudiant en L1**. C'est un projet Python 3.13 autonome (son propre `pyproject.toml`/`uv.lock`/`.venv`), indépendant des autres sous-projets d'`aelion/` (`indusense`, `indusense_ml`, `postgres-docker`) que décrit le [CLAUDE.md parent](../CLAUDE.md) — **ce projet n'y est pas mentionné**.

Deux cibles : classification binaire `abandon` (principale) + régression `moyenne_finale` (secondaire).

**Deux artefacts de rôles distincts, à ne pas confondre :**
- `notebooks/decrochage_etudiant.ipynb` = **livrable certifiant** (narration bout-en-bout C1→C9, plan imposé 0→15). Les cellules *orchestrent et expliquent*, elles ne redéfinissent pas la logique métier.
- `src/decrochage/` = **socle déterministe réutilisable**. Toute logique structurante (nettoyage, périmètre de features, entraînement, scoring) vit ici et est importée par le notebook comme par la CLI/API.

Ne jamais dupliquer dans le notebook une logique qui doit vivre dans le package.

## Documents de référence (lire avant de coder)

- `AGENTS.md` — liste exhaustive des commandes + conventions de style/commit (source pour les commandes ci-dessous).
- `ARCHITECTURE_PROJET.md` — architecture C7 (diagrammes, contrats I/O, modules, contraintes RGPD).
- `README.md` — vue d'ensemble et points méthodologiques.
- `docs/` — model card, industrialisation, monitoring, threat model, RGPD accountability.
- `reports/Enonce_cas_usage.pdf` — **source de vérité** des exigences de certification. Présent en local mais **non versionné** : il appartient à l'organisme de certification et n'est pas redistribué sur le dépôt public.

## Commandes

```powershell
uv sync --group notebook --group dev     # environnement complet (runtime + notebook + qualité)
uv run jupyter lab                        # ouvre le notebook certifiant
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/decrochage_etudiant.ipynb
uv run pytest                             # tous les tests
uv run pytest tests/test_training.py -k threshold   # un test ciblé
uv run ruff check .                       # lint (E501 ignoré — ne pas wrapper à la main)
uv run black --check .                    # formatage (100 colonnes)
```

CLI d'industrialisation (`decrochage = decrochage.cli:app`), toutes via `uv run` :

```powershell
uv run decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
uv run decrochage init-db                 # crée les tables (SQLite artifacts/decrochage.db par défaut)
uv run decrochage medallion-load <students.csv> <catalogue.csv>   # Bronze/Silver/Gold
uv run decrochage train <students.csv> <catalogue.csv>            # → artifacts/models/model_bundle.joblib
uv run decrochage predict <bundle> <input.csv> [--persist-db --batch-id <id>]
uv run decrochage drift-report <reference.csv> <current.csv> [--persist-db --batch-id <id>]
uv run decrochage purge-expired           # applique la rétention RGPD
uv run decrochage serve                   # API FastAPI (uvicorn)
```

La CI GitHub Actions (`.github/workflows/ci.yml`) rejoue `ruff` + `black --check` + `pytest` sur chaque push/PR.

## Le verrou anti-fuite (mécanisme central)

Toutes les décisions de périmètre de scoring sont **centralisées dans `features.py`** pour être testables et impossibles à contourner par inadvertance. Avant d'ajouter/utiliser une variable explicative, la qualifier : disponible à mi-S1 ? non identifiante ? non-leurre ?

- `scoring_feature_columns(df)` — seule source des colonnes explicatives autorisées.
- `assert_no_leakage(cols)` — garde-fou qui lève si une colonne interdite s'y glisse.
- `build_gold_dataset(...)` — **unique** source tabulaire pour l'entraînement ET le scoring notebook.

Colonnes exclues et pourquoi (constantes dans `features.py`) :
- `LEAKAGE_TARGET_COLS` (`moyenne_finale`) — fuite de données (résultat de fin de semestre).
- `LEAKAGE_TEMPORAL_COLS` (`moyenne_partiels_s1`, `nb_ue_validees_s1`) — **fuite temporelle** : consolidées en fin de S1, indisponibles au scoring à mi-S1.
- `ID_COLS` (`student_id`, `id_dossier`), `CONSTANT_COLS`, `LEURRE_COLS` (`groupe_td`, `couleur_carte_etudiante`, `jour_inscription`), `TEXT_COL` (`commentaire_tuteur`, dont on ne garde que `commentaire_present`).

## Flux clés

**Entraînement** (`training.train_model`) : `clean_raw` → `enrich_with_catalogue` → `add_engineered_features` → `build_gold_dataset` → split **train/validation/test** via `assign_split_labels` (même politique partout) → `Pipeline(impute+encode+scale+LogReg)` + `GridSearchCV(scoring="roc_auc")` → **seuil choisi par minimisation du coût métier sur la validation** (`select_threshold_by_cost`, `FN:FP = 5:1` par défaut ; le test l'est jamais touché) → métriques sur le test intact → `ModelBundle` joblib.

**Inférence** (`serving.predict_proba_abandon`) : DataFrame **brut** → `prepare_features` (`clean_raw` sans dédup → jointure catalogue → features → Gold sans labels, réindexé sur `bundle.feature_cols`) → `predict_proba` → `{proba_abandon ∈ [0,1], alerte 0/1}`. Le **bundle embarque le catalogue** pour être auto-suffisant : ne pas casser cette auto-suffisance.

Le nettoyage `preprocessing.clean_raw` est **partagé entraînement/inférence** (parsing FR : virgule décimale, `%`, `km` ; dates multi-formats ; harmonisation catégorielle). Toute nouvelle règle de nettoyage doit y passer, jamais dans le notebook seul.

## Persistance médaillon & RGPD (`persistence.py`)

- **Bronze** = brut restreint (payload JSON intégral, PII) → à restreindre/auditer/purger. **Silver/Gold** = identifiants directs pseudonymisés par **HMAC-SHA-256** dès Silver.
- `DECROCHAGE_PSEUDONYMIZATION_SECRET` est **obligatoire** avant toute persistance étudiante (lève sinon). Ne jamais le committer.
- Chaque `IngestionBatch` porte `expires_at` (`DECROCHAGE_RETENTION_DAYS`, 365 j) ; `purge-expired` supprime les lots échus. Toutes les opérations écrivent un `PrivacyAuditLog`.
- Défaut SQLite (`artifacts/decrochage.db`) pour rester exécutable sans infra ; `DECROCHAGE_DATABASE_URL` vise Postgres/autre (voir `compose.yaml`). Les moteurs sont mis en cache par URL.

## Tests fragiles à connaître

`tests/test_notebook_privacy.py` **assert sur des chaînes exactes du code source du notebook** (ex. `"X = gold_dataset[feature_cols].copy()"`, `"serving.predict_from_gold_dataset(modele_charge, X_demo)"`, absence de `df_raw`/`predict_proba_abandon(modele_charge`, absence de motif `ETU-\d{5}` dans les *outputs*). Ces tests garantissent que le notebook consomme le Gold pseudonymisé et n'expose aucun identifiant en clair. **Modifier la structure des cellules du notebook casse ces tests** — les mettre à jour de concert.

## Pièges & conventions

- `data/raw/` est **immuable** (livrable) ; `data/processed/` est transitoire et ignoré — la cible de persistance est la BDD, pas des CSV. Jeu principal ~5 200 lignes/33 colonnes, volontairement « sale ».
- Données `data/raw/`, `artifacts/`, volumes Postgres et le secret de pseudonymisation = **sensibles** ; ne pas committer bases générées, artefacts volumineux, ni secrets.
- Style : Black/Ruff 100 colonnes, `E501` ignoré (ne pas wrapper à la main). `snake_case` partout (y compris colonnes DataFrame), `PascalCase` pour les classes.
- Les performances rapportées valent sur **données synthétiques** — revalidation + A/B test avant tout déploiement réel (voir `docs/model_card.md`).
</content>
</invoke>
