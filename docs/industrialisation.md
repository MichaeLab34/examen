# Industrialisation

This project now separates the certification notebook from the operational path.
The notebook explains the C1-C9 reasoning; the package under `src/decrochage/`
contains reusable code for training, prediction, API serving, CLI operations and
monitoring.

## Operational Entry Points

- `decrochage check-data data/raw/decrochage_etudiants_complet_V5.csv data/raw/catalogue_formations_V5.csv`
  validates cleaning, catalogue join coverage and leakage guards.
- `decrochage train ... --output artifacts/models/model_bundle.joblib` trains a
  bundle with train/validation/test separation.
- `decrochage predict artifacts/models/model_bundle.joblib input.csv --output reports/predictions.csv`
  scores raw SI/LMS records.
- `decrochage drift-report reference.csv current.csv --output reports/drift_report.json`
  generates a PSI drift report.
- `decrochage serve` starts the FastAPI service.

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

This is intentionally a lightweight serving image: no notebook server, no local
database, and no presentation assets.
