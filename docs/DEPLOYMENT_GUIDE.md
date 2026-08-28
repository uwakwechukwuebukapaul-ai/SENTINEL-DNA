# Sentinel DNA V1 Deployment Guide

Set `SENTINEL_DNA_ENV` to `production`. Production requires protected `SENTINEL_DNA_SECRET_KEY` and `POSTGRES_PASSWORD` values. The release helper derives immutable image metadata from Git; operators must not maintain those values manually.

Use the controlled deployment adapter in `deployment/scripts/controlled_deploy.py`. An authorized provider must materialize the protected production configuration outside the repository; never use the repository `.env` as production authority. Prepare the deployment-owned Gate 1 artifact with `deployment/scripts/prepare_trusted_release_metadata.py`, then run the adapter in `--dry-run` or `--validate-only` mode before any explicitly authorized `--execute` operation. The adapter uses only `deployment/docker-compose.yml`, pins the verified immutable digest, runs the one-shot migration service, and recreates only the application service. The container runs as a non-root `sentinel` user and persists data under `/var/lib/sentinel`.

`GET /health` checks application and database availability. `GET /ready` additionally validates required registered services. Use the `deployment/docker-compose.yml` topology when an Nginx reverse proxy is required. Nginx is the public edge: port 80 redirects to HTTPS on port 443, while the application remains internal on port 5000. The proxy forwards `X-Forwarded-Proto=https`, `X-Forwarded-For`, and `X-Correlation-ID`; do not expose the application port directly to the public internet. The manual `deployment-contract` GitHub Actions workflow validates protected production configuration and provenance without assuming a remote hosting provider.

## Canonical production entrypoint

Only the WSGI/Gunicorn path is supported for production deployment:

```text
Dockerfile -> gunicorn wsgi:application -> wsgi.py -> app.create_app()
```

`app.py` and `main.py` are development/legacy Flask entrypoints. Dashboard-specific applications, archived applications, and other alternate modules are non-production and must not be selected by Compose, Gunicorn, or an operator command. The controlled deployment boundary uses only the checked-in `Dockerfile`, `deployment/docker-compose.yml`, and `wsgi:application` entrypoint.

## Current persistence boundary

PostgreSQL is the production and staging persistence backend. SQLite remains
supported for local development and tests. Redis is the internal runtime
dependency. The explicit migration job runs the complete authoritative chain
before application traffic is enabled; the application does not silently run
deployment migrations while importing WSGI.

| Domain data | Current boundary |
| --- | --- |
| Cases, notes, evidence, timeline, IOCs, incidents, analyst actions | Persistent SQLite tables and repositories |
| Investigations, reports, execution envelopes, provider observations, investigation quality, feedback | Persistent SQLite repositories |
| Audit records, tenant metadata, identity bindings, provider-tenant trust | Persistent SQLite tables/services |
| Billing and payment state | Persistent SQLite repositories/migrations |
| Intelligence and fusion | Mixed: SQLite-backed repositories where wired; process-local derived results in some engines |
| Replay data | Mixed: derived/process-local Customer Zero replay plus selected SQLite execution/report records; no dedicated immutable replay store |
| PostgreSQL and Redis Compose services | Internal production dependencies; PostgreSQL is initialized by the explicit migration job |

This boundary is not by itself a production-scale certification. Backup/restore,
multi-instance operation, and RPO/RTO evidence remain separate release gates.

## Local operator HTTPS validation

The checked-in local validation configuration is for `localhost` only. It is not a production CA configuration and must not be used as production certificate material. The certificate and private key must remain outside Git in a protected directory supplied at runtime through `SENTINEL_DNA_TLS_DIR`.

For a Windows operator validation run, use an already-installed certificate tool. `mkcert` is preferred when available. If it is unavailable, an operator may use the existing Git for Windows OpenSSL binary to create a short-lived localhost-only certificate, then trust that certificate only in the operator's current-user Windows trust store. Do not install tools automatically, commit the certificate or key, or disable certificate verification.

The protected directory must contain these PEM files:

```text
localhost.crt
localhost.key
```

The authorized protected configuration must contain `SENTINEL_DNA_TLS_DIR`
referencing this protected directory. Do not use a shell environment override
for controlled deployment variables; the adapter deliberately removes those
overrides before invoking Compose.

```powershell
python deployment/scripts/controlled_deploy.py `
  --reviewed-sha <reviewed-full-sha> `
  --expected-digest <verified-image-digest> `
  --env-file <AUTHORIZED_PROTECTED_ENV_FILE> `
  --metadata-file C:\ProgramData\Sentinel-DNA\release\metadata.json `
  --release-manifest <VERIFIED_RELEASE_MANIFEST> `
  --dry-run
```

Restrict the directory and key to the operator, SYSTEM, and administrators. Mounting is read-only inside nginx. Validate the actual configuration with `nginx -t`, verify that HTTP returns a 308 redirect to HTTPS, verify the certificate SAN for `localhost` or `127.0.0.1`, and verify `/health` and `/ready` over HTTPS without insecure certificate flags. Rotate or remove local-only material after validation; never treat it as production trust material.

## Backup and restore

Back up the persistent SQLite file before upgrades or migrations. Stop the application before a file-level restore. Keep the primary database untouched while validating a backup in a separate file, then verify `/ready` and retrieve a known report before placing the restored file into service. Retain at least one known-good backup and record its creation time. Do not begin backup/restore certification until Gate 1 is formally passed.

## Restart and rollback

Restart or rollback only through an approved operator procedure using the protected configuration and independently verified immutable image. Do not use the repository `.env`, mutable tags, or an ad-hoc Compose command. Preserve persistent volumes and repeat provenance, health, readiness, authorization, and report-retrieval checks before reopening traffic.
