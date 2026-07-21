# Threat Model

## Scope

The serving surface is a FastAPI service exposing dropout-risk prediction from
raw student records. Data is sensitive because it contains academic, engagement
and social-context variables.

## Key Threats And Controls

| Threat | Risk | Control |
|---|---|---|
| Spoofing | Unauthorized prediction calls | Optional `DECROCHAGE_API_KEY` with `X-API-Key` |
| Tampering | Invalid payload changes scoring behavior | Pydantic request validation and feature guard |
| Repudiation | No trace of scoring operations | Structured request log with `X-Request-ID`, route, status and duration |
| Information disclosure | Student data leaked through logs | Do not log payloads or API keys |
| Information disclosure | Direct identifiers stored in restricted Bronze | RBAC, no payload logging, retention purge, DPO-controlled access |
| Information disclosure | Direct identifiers propagated to analytical layers | HMAC-SHA-256 pseudonymization from Silver onward |
| Denial of service | Oversized or repeated prediction calls | API schema caps requests at 500 records and applies a configurable per-client rate limit |
| Elevation of privilege | Container escape impact | Docker image runs as non-root `appuser` |

## RGPD Notes

- Finality: academic support, not sanction.
- Minimization: identifiers are excluded from model features, restricted in Bronze and pseudonymized from Silver onward.
- Retention: batches have `expires_at`; `decrochage purge-expired` removes expired data.
- Human review: alerts are recommendations for support teams.
- Accountability: privacy actions are logged in `privacy_audit_log`.

## Production Deployment Gates

The application controls are executable in the prototype: API key, request
correlation without payload logging, per-client rate limiting, schema limits,
retention and pseudonymisation. A multi-instance deployment must replace the
in-memory limiter with a shared edge or Redis-backed limiter.

Before processing real student data, the DSI must provide managed secret
storage and encryption at rest with documented key rotation. The DPO must
validate the processing register and DPIA. These organisational approvals are
go-live gates and are not represented as completed by this repository.
