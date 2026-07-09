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
| Denial of service | Oversized prediction payload | API schema caps requests at 500 records |
| Elevation of privilege | Container escape impact | Docker image runs as non-root `appuser` |

## RGPD Notes

- Finality: academic support, not sanction.
- Minimization: identifiers are excluded from model features.
- Retention: scores should be kept only for the academic support window.
- Human review: alerts are recommendations for support teams.

## Open Production Work

Before real deployment, add infrastructure-level rate limiting, structured audit
logs with request IDs, secret management and DPO-approved retention settings.
