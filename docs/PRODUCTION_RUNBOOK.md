# Sentinel DNA Production Runbook

1. Validate the environment secret and database path.
2. Start with `docker compose up -d --build`.
3. Confirm `/health` and `/ready` return successful status.
4. Review logs for startup or database errors.
5. Back up the SQLite volume before upgrades.
6. Stop the service before restoring a database backup.

Never place passwords, API keys, or tokens in source control or request logs.
