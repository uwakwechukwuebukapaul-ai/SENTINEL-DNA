# Sentinel DNA production readiness

This repository uses `services.core.production_readiness.assess_production_readiness` as the machine-readable gate contract. Run:

```powershell
.\.venv\Scripts\python.exe -m deployment.production.readiness
```

The report uses `PASS`, `WARN`, `BLOCKED`, and `FAIL`. It never infers Docker, backup/restore, browser, or performance evidence. Those checks must be supplied by CI or the release operator. A local development run is therefore normally `PILOT READY`, not `PRODUCTION READY`.

Critical runtime gates are fail-closed: production secret validation, secure cookies, debug disabled, database connectivity, required services, and canonical tenant authority. The release gate is `PASS` only when all applicable gates have explicit passing evidence.

## Scorecard

| Gate | Evidence boundary |
| --- | --- |
| Architecture | Coordinator, orchestrator, runtime executor, repositories, read models, versioned projections |
| Security | Authentication V3, canonical authorization, secure cookie configuration, bounded requests, redaction |
| Tenant Isolation | Canonical authority and object-level tenant checks |
| API | Safe errors, correlation IDs, bounded request bodies, stable versioned contracts |
| Database | SQLite connectivity, WAL, foreign keys, busy timeout, bounded repository pagination |
| AI Safety | Provider-neutral gateway, sanitized evidence, uncertainty, advisory-only decisions |
| Investigation Reliability | Deterministic projections, leases, bounded retries, recovery |
| Operations | Queue, lease, notification and evaluation repositories |
| Observability | Correlation IDs, safe headers, request counters, health/readiness |
| Frontend | Authenticated workspace, redaction, state/error/empty handling |
| Deployment | WSGI/Gunicorn, non-root container, explicit secrets, persistent storage |
| Browser | Authenticated release certification and visual QA |
| Performance | Representative tenant baseline and bounded payload/query checks |
| Documentation | Security, deployment, operations, incident, AI, tenancy, observability, release docs |

## Release rule

The current supported deployment is a controlled pilot topology: one Gunicorn worker with SQLite persistence. Production requires a protected secret, secure cookies, a writable persistent database volume, backups, and a tested restore procedure. Horizontal scaling and a shared managed database remain separate milestones.

The repeatable local baseline is `tests/performance/test_baseline.py`. It measures queue API, workspace load, graph generation, report projection, operations dashboard, and SQL-bounded large-tenant pagination. Measurements are diagnostic baselines, not customer SLOs; target-environment load testing remains a release gate.
