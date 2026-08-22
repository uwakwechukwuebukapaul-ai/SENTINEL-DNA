# Deployment

The canonical production entrypoint is `wsgi:application` under Gunicorn. The container runs as the non-root `sentinel` user and stores SQLite data at `/var/lib/sentinel/soc.db`.

Required production settings:

```text
SENTINEL_DNA_ENV=production
SENTINEL_DNA_SECRET_KEY=<random secret, 32+ characters>
SENTINEL_DNA_SECURE_COOKIES=1
SENTINEL_DNA_DB_PATH=/var/lib/sentinel/soc.db
```

Use `deployment/docker-compose.yml` only with secrets injected from a protected environment or secret manager. Validate configuration before startup. `/health` is liveness plus database health; `/ready` verifies the database, foundational services, and operations repositories.

The current SQLite boundary supports one application worker. Back up the persistent volume before upgrades and validate restore. Do not claim horizontal production scaling until the database and queue boundary are migrated to infrastructure designed for it.
