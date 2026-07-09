# Monitoring Plan

## Signals

| Signal | Metric | Alert |
|---|---|---|
| Data drift | PSI on numeric features | `watch >= 0.10`, `alert >= 0.25` |
| Model performance | AUC / recall when labels arrive | AUC `< 0.85` or recall drop `> 10 pts` |
| Fairness | Recall and alert-rate gaps by subgroup | gap `> 10 pts` |
| Data quality | Missing-rate per key feature | `> 20%` |
| Operations | API readiness and error rate | `/ready` unavailable or 5xx spike |

## Cadence

- During the mid-S1 scoring window: run data-quality and drift checks on every
  batch, then persist the report with `decrochage drift-report --persist-db
  --batch-id <id>`.
- Monthly: review alert rate, subgroup metrics and support-team feedback.
- Annually: retrain with the next labelled cohort and compare champion vs
  challenger.

## Actions

1. Investigate data collection changes when PSI enters `watch`.
2. Freeze automated re-use and trigger model review when PSI enters `alert`.
3. Recalibrate threshold if the intervention capacity or FN/FP cost ratio
   changes.
4. Archive obsolete model bundles after a replacement has been validated.

## Persistence

Drift reports are written as JSON artifacts and can also be stored in the
`gold_drift_report` SQL table. This keeps the monitoring decision attached to an
ingestion `batch_id`, with `status`, `watch_count`, `alert_count` and the full
report payload available for dashboards or later audits.
