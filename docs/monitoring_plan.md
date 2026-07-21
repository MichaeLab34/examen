# Monitoring Plan

## Signals

| Signal | Metric | Alert |
|---|---|---|
| Data drift | PSI on numeric features | `watch >= 0.10`, `alert >= 0.25` |
| Model performance | AUC / recall when labels arrive | AUC `< 0.85` or recall drop `> 10 pts` |
| Fairness | Recall and alert-rate gaps by subgroup | gap `> 10 pts` |
| Data quality | Missing-rate per key feature | `> 20%` |
| Operations | API readiness and error rate | `/ready` unavailable or 5xx > 1% for 5 min |
| Scheduled jobs | External heartbeat | expected ping absent |

## Cadence

- During the mid-S1 scoring window: run data-quality and drift checks on every
  batch, then persist the report with `decrochage drift-report --persist-db
  --batch-id <id>`.
- Monthly: review alert rate, subgroup metrics, unresolved incidents and
  support-team feedback.
- Annually: retrain when the next labelled cohort is available, then compare
  `candidate` vs `production` on recall, AUC and fairness before human approval.

## Actions

1. Investigate data collection changes when PSI enters `watch`.
2. Freeze automated re-use and trigger model review when PSI enters `alert`;
   without fresh labels, investigate the collection rather than retraining blindly.
3. Recalibrate threshold if the intervention capacity or FN/FP cost ratio
   changes.
4. Promote only after non-regression of recall, AUC >= 0.85, subgroup recall
   gap <= 10 points and explicit human approval.
5. Roll back the MLflow `production` alias when a validated model regresses in Run.

## Alert Routing

Grafana routes operational warnings to the university team channel and waits
five continuous minutes before firing. The DSI on-call path is reserved for the
mid-S1 scoring window because this is a replayable batch service, not a 24/7
life-critical API. `DECROCHAGE_HEALTHCHECK_URL` covers silence from scoring,
drift and purge jobs.

## Persistence

Drift reports are written as JSON artifacts and can also be stored in the
`gold_drift_report` SQL table. This keeps the monitoring decision attached to an
ingestion `batch_id`, with `status`, `watch_count`, `alert_count` and the full
report payload available for dashboards or later audits.
