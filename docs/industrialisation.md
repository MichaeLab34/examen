# Industrialisation

This project now separates the certification notebook from the operational path.
The notebook explains the C1-C9 reasoning; the package under `src/decrochage/`
contains reusable code for training, prediction, API serving, CLI operations and
monitoring.

## Operational Entry Points

- `decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  validates cleaning, catalogue join coverage and leakage guards.
- `decrochage init-db` creates the SQL tables used for Bronze/Silver/Gold
  persistence. By default the database is `artifacts/decrochage.db`, while the
  production-like Docker stack uses Postgres.
- `decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  persists raw rows in Bronze, cleaned/pseudonymized rows in Silver, and
  ML-ready feature rows in Gold.
- `decrochage purge-expired` deletes batches past their RGPD retention window.
- `decrochage train ... --output artifacts/models/model_bundle.joblib` trains a
  bundle with train/validation/test separation.
- `decrochage predict artifacts/models/model_bundle.joblib input.csv --output reports/predictions.csv`
  scores raw SI/LMS records. Add `--persist-db --batch-id <id>` to store the
  predictions in the Gold table.
- `decrochage drift-report reference.csv current.csv --output reports/drift_report.json`
  generates a PSI drift report. Add `--persist-db --batch-id <id>` to store the
  monitoring result in the Gold table.
- `decrochage serve` starts the FastAPI service.

## Database & Medallion Architecture

The persistence layer is implemented in `src/decrochage/persistence.py` with
SQLAlchemy. `DECROCHAGE_DATABASE_URL` can point to another SQL backend; when it
is not set, SQLite is used locally. For a production-like local stack, use
Postgres through Docker Compose:

```bash
cp .env.example .env
# edit POSTGRES_PASSWORD and DECROCHAGE_PSEUDONYMIZATION_SECRET
docker compose up -d postgres
uv run decrochage init-db
uv run decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
```

The local database contains student records and is intentionally ignored by Git.
The pseudonymization secret must stay outside version control.

- Bronze tables keep one raw payload per source row with `batch_id`, `parse_ok`
  and `rejected_reason` fields for traceability. This layer can contain direct
  identifiers and must therefore be restricted, audited and purged.
- Silver tables store deterministic cleaned/normalized records and catalogue
  references. Direct identifiers are replaced by deterministic
  HMAC-SHA-256 pseudonyms.
- Gold tables store training features without leakage columns, deterministic
  `train`/`validation`/`test` split labels, predictions and drift reports.
- `privacy_audit_log` stores accountability events without direct student data.

The first operational sequence is:

```bash
decrochage init-db
decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv
```

Use the returned `batch_id` when persisting downstream predictions or drift
reports.

## API Contract

- `GET /health`: liveness, returns 200 when the process runs.
- `GET /ready`: readiness, returns 200 only when the model bundle is loaded.
- `POST /predict`: accepts raw student records and returns `proba_abandon` plus
  `alerte`.

Set `DECROCHAGE_MODEL_PATH` to select the model bundle. Set
`DECROCHAGE_API_KEY` to require an `X-API-Key` header. Set
`DECROCHAGE_PSEUDONYMIZATION_SECRET` before persisting Silver, Gold or
prediction rows.

## Deployment

Build and run locally:

```bash
docker compose up --build
```

This is intentionally a lightweight serving image: no notebook server and no
presentation assets. Database persistence is handled by the SQLAlchemy layer and
can use the local SQLite default or the Compose Postgres service.
