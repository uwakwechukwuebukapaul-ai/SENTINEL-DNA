# Production Runbook

1. Apply the SaaS PostgreSQL migration before deploying the API.
2. Deploy through Helm; verify `/healthz`, `/readyz`, `/version`, and restricted `/metrics`.
3. Confirm PostgreSQL backups, Redis availability, secret references, TLS/WAF, and network policies.
4. Run `SENTINEL_DNA_TEST_POSTGRES_URL=... python -m pytest tests` and the equivalent Redis/Kubernetes validation in the release environment.
5. Monitor authentication denials, 5xx responses, job failures, job retries, and investigation duration metrics.

Rollback: stop new traffic, retain PostgreSQL/Redis volumes, roll back the API image, and re-run readiness checks. Do not roll back a schema migration without an approved database rollback plan.
