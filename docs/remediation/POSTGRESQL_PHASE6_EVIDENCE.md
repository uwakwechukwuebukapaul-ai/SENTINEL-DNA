# PostgreSQL production readiness remediation — Phase 6 evidence

Generated: 2026-08-26

## Scope and custody

- Branch: `remediation/postgresql-production-readiness`
- Protected release commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- Phase 6 scope: controlled deployment configuration integration
- Deployment performed: none
- Credentials or external database access: none

## Change evidence

| Objective | Evidence |
| --- | --- |
| Production URL gate | `validate_configuration(..., require_postgresql=True)` reports `DATABASE_URL:missing` when controlled production validation has no PostgreSQL URL. |
| URL validation | PostgreSQL URL schemes and network locations remain validated without serializing URL values. |
| Controlled deploy wiring | `ControlledDeploymentAdapter` enables the required PostgreSQL gate before deployment execution. |
| Compose integration | `docker-compose.yml` already requires `DATABASE_URL` through Compose interpolation and passes it to the application. |
| Application boundary | The runtime backend factory remains the fail-closed process boundary; explicit SQLite paths remain limited to compatibility/test callers. |

## Validation

The new deployment contract assertion passes. The broader deployment test
subset was run from the shared working tree and its fixture-dependent failures
stopped at the intentional clean-worktree gate because the remediation changes
are uncommitted in this read-only-`.git` environment; those failures are not
configuration regressions. A clean-clone full regression will be regenerated
after the current Phase 5/6 source set is assembled.
