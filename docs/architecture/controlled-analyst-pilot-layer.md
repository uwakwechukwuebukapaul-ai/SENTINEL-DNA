# Controlled Analyst Pilot Layer

The controlled analyst pilot is a tenant-scoped workflow overlay for a
bounded, synthetic-only analyst evaluation. It provides manager-led pilot
account/tenant onboarding, explicit analyst feedback and review permissions,
append-only feedback capture, manager review transitions, compensating review
events, and a hash-linked tenant-scoped pilot audit trail.

## Security boundary

Gate 4 external custody verification is unchanged. This layer does not load,
replace, or infer the trusted browser provider and does not turn a failed
`TB_PROVIDER_*` check into success. Any browser/runtime activation must still
be performed by the existing Gate 4 deployment scripts and must satisfy every
existing provider and custody check.

Pilot investigation writes remain subject to the existing canonical tenant,
analyst authorization, synthetic-data, approved-scenario, and fail-closed
checks. `synthetic_only` and `external_custody_required` are contract fields,
not claims that external custody has been verified.

## API surface

All write endpoints require the existing same-origin synchronizer CSRF token.
Tenant and actor identifiers are taken from the canonical security context,
never from request payloads.

| Method | Endpoint | Permission | Purpose |
| --- | --- | --- | --- |
| POST | `/api/controlled-analyst-pilot/onboard` | `pilot:manage` | Provision and register an isolated pilot account |
| GET | `/api/controlled-analyst-pilot/current` | `pilot:read` | Read the current analyst pilot tenant |
| POST | `/api/controlled-analyst-pilot/feedback` | `pilot:feedback` | Capture immutable analyst feedback |
| GET | `/api/controlled-analyst-pilot/feedback` | `pilot:feedback:read` | Read tenant-scoped feedback |
| POST | `/api/controlled-analyst-pilot/reviews` | `pilot:review` | Submit an investigation review |
| GET | `/api/controlled-analyst-pilot/reviews` | `pilot:review:read` | Read current review projections |
| POST | `/api/controlled-analyst-pilot/reviews/{id}/transition` | `pilot:review:manage` | Accept, reject, or request more evidence |
| POST | `/api/controlled-analyst-pilot/reviews/{id}/reopen` | `pilot:review:manage` | Add a compensating reopen event |
| POST | `/api/controlled-analyst-pilot/reviews/{id}/withdraw` | `pilot:review:manage` | Add a compensating withdrawal event |
| GET | `/api/controlled-analyst-pilot/audit` | `pilot:audit:read` | Read manager-visible pilot audit events |

Suspension/resumption endpoints are available to managers for reversible
operational pauses. Revocation remains a terminal security control and is
delegated to the existing bounded provisioner as well as recorded in the
overlay event stream.

## Persistence and migration

`database/migrations/010_controlled_analyst_pilot.py` creates the overlay
tables and append-only database guards. It is exposed as
`CONTROLLED_ANALYST_PILOT_MIGRATIONS`, an explicitly selected chain composed
of the existing core/staging chain plus version 010. It is not added to the
default production or Gate 4/FAVP chains. The application service also
performs an idempotent schema assertion so a missing table cannot become an
authorization success.

Feedback and review records are never updated or deleted. A correction is a
new review event (`reopened` or `withdrawn`), preserving the original analyst
submission and audit history.
