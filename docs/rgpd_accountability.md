# RGPD Accountability

This document maps the Sprint 1 RGPD expectations to concrete controls in this
project. It is a certification proof, not a substitute for a DPO sign-off.

## Data Classification

| Category | Columns | Treatment |
|---|---|---|
| Direct identifiers / PII | `student_id`, `id_dossier` | Kept raw only in restricted Bronze for traceability; HMAC-SHA-256 pseudonymization from Silver onward; excluded from model features |
| Quasi-identifiers | `age`, `filiere`, `etablissement_origine`, `boursier`, dates | Kept only when useful for support-risk modeling; monitored for fairness and reidentification risk |
| Sensitive/proxy attributes | `sexe`, `boursier`, `etablissement_origine` | Used only under human-review framing; subgroup metrics monitored |
| Risk scores | `proba_abandon`, `alerte` | Stored in Gold with `batch_id`, retention window and audit log |

## Seven RGPD Principles

| Principle | Project Control | Evidence |
|---|---|---|
| Lawfulness, fairness, transparency | Academic support purpose, no sanction, students must be informed before real deployment | Notebook section 4, model card, support notes |
| Purpose limitation | Use limited to mid-S1 dropout-risk support | README, model card intended use |
| Data minimization | Direct IDs excluded from features; PII restricted in Bronze and pseudonymized from Silver onward | `features.py`, `persistence.py`, tests |
| Accuracy | Deterministic cleaning and catalogue join checks | `preprocessing.py`, `check-data` CLI |
| Storage limitation | `expires_at` on batches; `decrochage purge-expired` | `ingestion_batch`, `purge_expired_batches` |
| Integrity & confidentiality | API key option, non-root container, `.env` secrets, Postgres stack, no payload logging | `api.py`, Dockerfile, Compose, threat model |
| Accountability | `privacy_audit_log`, model card, threat model, documented RGPD matrix | `privacy_audit_log`, this document |

## Pseudonymization

Database persistence requires `DECROCHAGE_PSEUDONYMIZATION_SECRET` because the
Silver, Gold and prediction layers replace direct identifiers with HMAC
pseudonyms. The HMAC secret must be stored outside Git and managed as a
production secret. The same student keeps the same pseudonym across batches,
which supports longitudinal monitoring while avoiding clear identifiers outside
the restricted Bronze layer.

Pseudonymization is not anonymization: the data remains personal data under RGPD
because the secret allows controlled linkage. Row-level exports must therefore
stay internal unless a separate anonymization study is performed.

## Retention

`DECROCHAGE_RETENTION_DAYS` defines the support window, defaulting to 365 days.
Each ingestion batch receives an `expires_at`. The command below removes expired
batches and their Bronze/Silver/Gold rows, while writing an audit event:

```bash
uv run decrochage purge-expired
```

## Production Checklist Before Real Student Data

- Validate the legal basis with the DPO; for a public university, document
  whether this is a public-interest mission rather than legitimate interest.
- Publish student information notice: purpose, data categories, retention, human
  review, rights of access/rectification/opposition.
- Store secrets in a managed secret vault, not in `.env` files.
- Enable platform encryption at rest and role-based DB access.
- Add request-level audit logs without raw payloads.
- Complete a DPIA/AIPD if required by the DPO.
- Run a reidentification/anonymization study before any row-level export.
