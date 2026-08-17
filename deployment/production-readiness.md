# Sentinel DNA production readiness

Controlled V1 deployment uses one Gunicorn worker because report persistence is SQLite-backed. Set these values before startup:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_SECRET_KEY=<32+ character random secret>
SENTINEL_DNA_SECURE_COOKIES=1
SENTINEL_DNA_DB_PATH=/var/lib/sentinel/soc.db
```

The database parent directory must already exist and be writable by the service user. Mount `/var/lib/sentinel` as persistent storage, back it up before upgrades, and validate restore procedures. Horizontal scaling and shared managed database infrastructure are future milestones; do not run multiple application workers against the same SQLite file.

The application exposes `/health` for liveness and `/ready` for readiness. Readiness fails when required services or SQLite are unavailable. Never place secrets in source control or request logs.
