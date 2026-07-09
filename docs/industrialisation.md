# Industrialisation

This project now separates the certification notebook from the operational path.
The notebook explains the C1-C9 reasoning; the package under `src/decrochage/`
contains reusable code for training, prediction, API serving, CLI operations and
monitoring.

## Operational Entry Points

- `decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  validates cleaning, catalogue join coverage and leakage guards.
- `decrochage init-db` creates the SQL tables used for Bronze/Silver/Gold
  persistence. By default the database is `artifacts/decrochage.db`.
- `decrochage medallion-load data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  persists raw rows in Bronze, cleaned/enriched rows in Silver, and ML-ready
  feature rows in Gold.
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
is not set, SQLite is used locally. The local database contains student records
and is intentionally ignored by Git.

- Bronze tables keep one raw payload per source row with `batch_id`, `parse_ok`
  and `rejected_reason` fields for traceability.
- Silver tables store deterministic cleaned/normalized records and catalogue
  references.
- Gold tables store training features without leakage columns, deterministic
  `train`/`validation`/`test` split labels, predictions and drift reports.

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
`DECROCHAGE_API_KEY` to require an `X-API-Key` header.

## Deployment

Build and run locally:

```bash
docker build -t decrochage-api .
docker run --rm -p 8000:8000 \
  -e DECROCHAGE_MODEL_PATH=/app/artifacts/models/model_bundle.joblib \
  -v "$PWD/artifacts:/app/artifacts:ro" \
  decrochage-api
```

This is intentionally a lightweight serving image: no notebook server and no
presentation assets. Database persistence is handled by the SQLAlchemy layer and
can use the local SQLite default or an external database URL.
