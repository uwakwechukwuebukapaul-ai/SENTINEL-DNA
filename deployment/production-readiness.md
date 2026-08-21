# Sentinel DNA production readiness

Controlled V1 deployment uses one Gunicorn worker because report persistence is SQLite-backed. Set these values before startup:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_SECRET_KEY=<32+ character random secret>
SENTINEL_DNA_SECURE_COOKIES=1
SENTINEL_DNA_DB_PATH=/var/lib/sentinel/soc.db
```

The database parent directory must already exist and be writable by the service user. Mount `/var/lib/sentinel` as persistent storage, back it up before upgrades, and validate restore procedures. Horizontal scaling and shared managed database infrastructure are future milestones; do not run multiple application workers against the same SQLite file.

The application exposes `/health` for liveness and `/ready` for readiness. Readiness fails when required services or SQLite are unavailable. Put Nginx or another controlled reverse proxy at the public boundary, terminate TLS there, keep port 5000 private, and forward `X-Forwarded-Proto`, `X-Forwarded-For`, and `X-Correlation-ID`.

Before upgrades, create a SQLite backup without overwriting the primary file. Restore into a separate database location first and verify a known report, tenant authorization, governance metadata, `/health`, and `/ready`. For rollback, stop the application, deploy the previous known-good image/configuration, preserve the persistent volume, and restore the last validated backup only when necessary.

Never place secrets in source control or request logs. Review structured logs for correlation IDs and confirm that credentials, tokens, provider responses, authorization payloads, raw IOCs, and exception messages are absent.
