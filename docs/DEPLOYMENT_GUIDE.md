# Sentinel DNA V1 Deployment Guide

Set `SENTINEL_DNA_ENV` to `production`. Production requires protected `SENTINEL_DNA_SECRET_KEY` and `POSTGRES_PASSWORD` values. The release helper derives immutable image metadata from Git; operators must not maintain those values manually.

Use a protected `.env` only for local secrets, derive release metadata with `deployment/scripts/release_metadata.py`, validate with `deployment/scripts/validate_deployment_config.py`, and use only `deployment/docker-compose.yml`. The container runs as a non-root `sentinel` user and persists data under `/var/lib/sentinel`. V1 uses one Gunicorn worker because SQLite is the current persistence boundary; do not add workers or replicas against the same database file.

`GET /health` checks application and database availability. `GET /ready` additionally validates required registered services. Use the `deployment/docker-compose.yml` topology when an Nginx reverse proxy is required. The checked-in Nginx configuration is an HTTP forwarding baseline; terminate TLS at the deployment edge, forward `X-Forwarded-Proto`, `X-Forwarded-For`, and `X-Correlation-ID`, and do not expose the application port directly to the public internet. The manual `deployment-contract` GitHub Actions workflow validates protected production configuration and provenance without assuming a remote hosting provider.

## Backup and restore

Back up the persistent SQLite file before upgrades or migrations. Stop the application before a file-level restore. Keep the primary database untouched while validating a backup in a separate file, then verify `/ready` and retrieve a known report before placing the restored file into service. Retain at least one known-good backup and record its creation time.

## Restart and rollback

Restart with `docker compose restart sentinel-dna` and verify `/health` and `/ready`. For rollback, stop the stack, deploy the previous known-good image/configuration, preserve the persistent volume, and restore the last validated SQLite backup only when the database itself must be rolled back. Re-run health, readiness, authorization, and report-retrieval checks before reopening traffic.
