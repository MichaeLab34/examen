# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python 3.13 ML project for early detection of student dropout risk. Reusable package code lives in `src/decrochage/`: `preprocessing.py` cleans raw inputs, `features.py` defines anti-leakage feature engineering, `training.py` trains a bundle, `serving.py` predicts, `persistence.py` stores Bronze/Silver/Gold SQL layers, and `api.py`/`cli.py` expose production paths. The main certification deliverable is `notebooks/decrochage_etudiant.ipynb`. Treat `reports/Enonce_cas_usage.pdf` as the source of truth for certification requirements. Production notes are in `docs/`.

## Build, Test, and Development Commands

- `uv sync --group dev` installs runtime, notebook, and quality tooling from `pyproject.toml`; `dev` includes `notebook` so a later dev sync does not remove Jupyter.
- `uv run jupyter lab` starts the local notebook environment.
- `uv run jupyter nbconvert --to notebook --execute --inplace notebooks/decrochage_etudiant.ipynb` executes the full notebook workflow.
- `uv run decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv` validates data and leakage guards.
- `uv run decrochage init-db` creates the local SQL database at `artifacts/decrochage.db` unless `DECROCHAGE_DATABASE_URL` is set.
- `uv run decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv` persists Bronze raw restricted rows, Silver cleaned/pseudonymized rows, and Gold ML features.
- `uv run decrochage purge-expired` applies the RGPD retention policy to expired database batches.
- `uv run decrochage train data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv` trains `artifacts/models/model_bundle.joblib`.
- `uv run decrochage serve` starts the FastAPI service.
- `uv run pytest` runs automated tests.
- `uv run ruff check .` runs lint checks.
- `uv run black --check .` verifies formatting.
- `uv build` builds the package with Hatchling.

## Coding Style & Naming Conventions

Use Black formatting with 100-character lines. Ruff is configured with the same line length and ignores `E501`; do not hand-wrap just to satisfy line-length linting. Use 4-space indentation, `snake_case` for modules, functions, variables, and DataFrame columns, and `PascalCase` for classes such as model bundle types. Keep reusable logic in `src/decrochage/`; notebook cells should orchestrate and explain, not duplicate production logic.

## Testing Guidelines

Tests live in `tests/` and use `pytest`. Prefer small DataFrame fixtures that exercise parsing, leakage guards, training threshold logic, prediction contracts, drift reports, and API readiness/prediction behavior.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries in French or English, for example `Corrige le warning SHAP...` and `Refactor code structure...`. Keep commits concise, action-oriented, and scoped to one change. Pull requests should describe the change, list validation commands run, mention any data/model artifacts regenerated, and include screenshots or exported figures when notebook outputs or presentation visuals change.

## Security & Agent-Specific Instructions

Treat `data/raw/`, generated databases under `artifacts/`, Postgres volumes, and `DECROCHAGE_PSEUDONYMIZATION_SECRET` as sensitive. Do not commit credentials, local notebooks with secrets, generated databases, or large regenerated artifacts unless they are required deliverables. The related Obsidian vault is at `/Users/michael/ObsidianVaults/Formation_IA/`. Never use `rm -rf`; use `trash <path>` so files remain recoverable.
