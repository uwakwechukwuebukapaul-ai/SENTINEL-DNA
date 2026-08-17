# Sentinel DNA Production Runbook

1. Set `SENTINEL_DNA_ENV=production`, a random 32+ character `SENTINEL_DNA_SECRET_KEY`, `SENTINEL_DNA_SECURE_COOKIES=1`, and an explicit writable `SENTINEL_DNA_DB_PATH`.
2. Start with `docker compose up -d --build`.
3. Confirm `/health` and `/ready` return successful status.
4. Review structured logs for startup, correlation ID, or database errors.
5. Back up the persistent SQLite volume before upgrades.
6. Stop the service before restoring a database backup.
7. Keep the single-worker topology; shared database infrastructure is a future scaling milestone.

Never place passwords, API keys, or tokens in source control or request logs.
