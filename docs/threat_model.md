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
| Repudiation | No trace of scoring operations | Add request logging in the target deployment |
| Information disclosure | Student data leaked through logs | Do not log payloads or API keys |
| Information disclosure | Direct identifiers stored in restricted Bronze | RBAC, no payload logging, retention purge, DPO-controlled access |
| Information disclosure | Direct identifiers propagated to analytical layers | HMAC-SHA-256 pseudonymization from Silver onward |
| Denial of service | Oversized prediction payload | API schema caps requests at 500 records |
| Elevation of privilege | Container escape impact | Docker image runs as non-root `appuser` |

## RGPD Notes

- Finality: academic support, not sanction.
- Minimization: identifiers are excluded from model features, restricted in Bronze and pseudonymized from Silver onward.
- Retention: batches have `expires_at`; `decrochage purge-expired` removes expired data.
- Human review: alerts are recommendations for support teams.
- Accountability: privacy actions are logged in `privacy_audit_log`.

## Open Production Work

Before real deployment, add infrastructure-level rate limiting, request-level
audit logs, managed secret storage, encryption at rest controlled by the hosting
platform and formal DPO validation of the register/DPIA.
