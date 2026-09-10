# Sentinel DNA production readiness

Production persistence is PostgreSQL-backed through the authoritative
`DATABASE_URL`. SQLite remains available for local testing and legacy recovery
tools; repository SQL migration is a later phase. Only the following values
are protected secrets:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_SECRET_KEY=<32+ character random secret>
POSTGRES_PASSWORD=<protected database password>
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>
SENTINEL_DNA_SECURE_COOKIES=1
```

The release process derives the immutable image tag, Git revision labels, and UTC creation timestamp from the checked-out commit. Use `deployment/scripts/release_metadata.py` and `deployment/scripts/validate_deployment_config.py`; do not maintain release metadata manually or commit generated environment files.

`DATABASE_URL` takes precedence over `SENTINEL_DNA_DB_PATH` whenever it is
configured. Production backend resolution fails closed if the URL is missing
or not PostgreSQL. Phase 1 does not perform a deployment or connect to an
external database.

The application exposes `/health` for liveness and `/ready` for readiness. Put
Nginx or another controlled reverse proxy at the public boundary, terminate
TLS there, keep port 5000 private, and forward `X-Forwarded-Proto`,
`X-Forwarded-For`, and `X-Correlation-ID`.

Before upgrades, create a SQLite backup without overwriting the primary file. Restore into a separate database location first and verify a known report, tenant authorization, governance metadata, `/health`, and `/ready`. For rollback, stop the application, deploy the previous known-good image/configuration, preserve the persistent volume, and restore the last validated backup only when necessary.

Never place secrets in source control or request logs. Review structured logs for correlation IDs and confirm that credentials, tokens, provider responses, authorization payloads, raw IOCs, and exception messages are absent.
