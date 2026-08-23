# Sentinel DNA V1 Deployment Guide

Set `SENTINEL_DNA_ENV` to `production`. Production requires protected `SENTINEL_DNA_SECRET_KEY` and `POSTGRES_PASSWORD` values. The release helper derives immutable image metadata from Git; operators must not maintain those values manually.

Use a protected `.env` only for local secrets, derive release metadata with `deployment/scripts/release_metadata.py`, validate with `deployment/scripts/validate_deployment_config.py`, and use only `deployment/docker-compose.yml`. The container runs as a non-root `sentinel` user and persists data under `/var/lib/sentinel`. V1 uses one Gunicorn worker because SQLite is the current persistence boundary; do not add workers or replicas against the same database file.

`GET /health` checks application and database availability. `GET /ready` additionally validates required registered services. Use the `deployment/docker-compose.yml` topology when an Nginx reverse proxy is required. Nginx is the public edge: port 80 redirects to HTTPS on port 443, while the application remains internal on port 5000. The proxy forwards `X-Forwarded-Proto=https`, `X-Forwarded-For`, and `X-Correlation-ID`; do not expose the application port directly to the public internet. The manual `deployment-contract` GitHub Actions workflow validates protected production configuration and provenance without assuming a remote hosting provider.

## Local operator HTTPS validation

The checked-in local validation configuration is for `localhost` only. It is not a production CA configuration and must not be used as production certificate material. The certificate and private key must remain outside Git in a protected directory supplied at runtime through `SENTINEL_DNA_TLS_DIR`.

For a Windows operator validation run, use an already-installed certificate tool. `mkcert` is preferred when available. If it is unavailable, an operator may use the existing Git for Windows OpenSSL binary to create a short-lived localhost-only certificate, then trust that certificate only in the operator's current-user Windows trust store. Do not install tools automatically, commit the certificate or key, or disable certificate verification.

The protected directory must contain these PEM files:

```text
localhost.crt
localhost.key
```

Set the directory only in the operator's local PowerShell session before Compose validation and deployment:

```powershell
$env:SENTINEL_DNA_TLS_DIR = "C:\Users\<operator>\AppData\Local\Sentinel-DNA\tls"
docker compose --env-file .env -f deployment/docker-compose.yml config --quiet
```

Restrict the directory and key to the operator, SYSTEM, and administrators. Mounting is read-only inside nginx. Validate the actual configuration with `nginx -t`, verify that HTTP returns a 308 redirect to HTTPS, verify the certificate SAN for `localhost` or `127.0.0.1`, and verify `/health` and `/ready` over HTTPS without insecure certificate flags. Rotate or remove local-only material after validation; never treat it as production trust material.

## Backup and restore

Back up the persistent SQLite file before upgrades or migrations. Stop the application before a file-level restore. Keep the primary database untouched while validating a backup in a separate file, then verify `/ready` and retrieve a known report before placing the restored file into service. Retain at least one known-good backup and record its creation time. Do not begin backup/restore certification until Gate 1 is formally passed.

## Restart and rollback

Restart only the required service with `docker compose --env-file .env -f deployment/docker-compose.yml restart app` or `nginx` as directed by the approved procedure, and verify `/health` and `/ready` over HTTPS. For rollback, stop the stack, deploy the previous known-good image/configuration, preserve the persistent volume, and restore the last validated SQLite backup only when the database itself must be rolled back. Re-run health, readiness, authorization, and report-retrieval checks before reopening traffic.
