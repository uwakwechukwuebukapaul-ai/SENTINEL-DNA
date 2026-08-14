# Sentinel DNA Staging Deployment

## Deployment steps

1. Install Docker and Docker Compose.
2. Copy `.env.example` to `.env`.
3. Set `SENTINEL_DNA_ENV=staging` and provide a non-placeholder secret of at least 32 characters.
4. Confirm the configured SQLite volume path is writable by the container.
5. Run `sh deployment/scripts/deploy.sh`.
6. If using Nginx, mount `deployment/nginx/sentinel.conf` into the reverse proxy and route it to the Compose service.

## Configuration requirements

Required values are `SENTINEL_DNA_ENV`, `SENTINEL_DNA_SECRET_KEY`, and `SENTINEL_DNA_DB_PATH`. Staging uses synthetic or approved test data only. Never use production secrets or production databases.

## Health checks

Run `sh deployment/scripts/health_check.sh`. Both `/health` and `/ready` must succeed. `/ready` verifies database connectivity and required service registration.

## Rollback

Stop the current deployment, restore the previous image or Git revision, and restart with `docker compose up -d`. Restore the SQLite volume only from a verified staging backup. Do not perform schema migrations as part of this deployment.
