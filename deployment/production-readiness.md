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

For the active-container validator, the release metadata has this exact
format:

| Variable | Required value |
| --- | --- |
| `SENTINEL_DNA_IMAGE_TAG` | the lowercase 40-character `git rev-parse HEAD` value; this is the local Compose tag, without a `sha-` prefix |
| `SENTINEL_DNA_IMAGE_REVISION` | the lowercase 9-character `git rev-parse --short=9 HEAD` prefix |
| `SENTINEL_DNA_IMAGE_REVISION_FULL` | the lowercase 40-character `git rev-parse HEAD` value |
| `SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE` | an absolute path outside the repository to the deployment-owned, regular, non-symlink, non-writable JSON file containing exactly `release_sha` and `image_digest` |

The published GHCR reference uses a separate `sha-<full SHA>` tag. Do not put
that registry tag in `SENTINEL_DNA_IMAGE_TAG`; `deployment/docker-compose.yml`
expects the raw full SHA and the validator compares all three Git values to
the checked-out `HEAD`. Generate the three Git values from the reviewed
checkout and set the trusted metadata path after
`prepare_trusted_release_metadata.py` has created the file:

```powershell
$protectedEnv = "C:\ProgramData\Sentinel-DNA\production.env"
$trustedMetadata = "C:\ProgramData\Sentinel-DNA\release\metadata.json"
$release = python deployment/scripts/release_metadata.py --format json | ConvertFrom-Json
$env:SENTINEL_DNA_IMAGE_TAG = $release.SENTINEL_DNA_IMAGE_TAG
$env:SENTINEL_DNA_IMAGE_REVISION = $release.SENTINEL_DNA_IMAGE_REVISION
$env:SENTINEL_DNA_IMAGE_REVISION_FULL = $release.SENTINEL_DNA_IMAGE_REVISION_FULL
$env:SENTINEL_DNA_IMAGE_CREATED = $release.SENTINEL_DNA_IMAGE_CREATED
$env:SENTINEL_DNA_GATE1_TRUSTED_METADATA_FILE = $trustedMetadata
$env:SENTINEL_DNA_IMAGE_DIGEST = "sha256:<verified-64-lowercase-hex-digest>"
```

The protected environment file must also provide `SENTINEL_DNA_SECRET_KEY`,
`POSTGRES_PASSWORD`, `DATABASE_URL`, `SENTINEL_DNA_ENV=production`, and
`SENTINEL_DNA_SECURE_COOKIES=1`. The trusted metadata JSON must bind
`release_sha` to `SENTINEL_DNA_IMAGE_REVISION_FULL` and `image_digest` to
`SENTINEL_DNA_IMAGE_DIGEST`; a path, digest, or release mismatch fails closed.

`DATABASE_URL` takes precedence over `SENTINEL_DNA_DB_PATH` whenever it is
configured. The production Compose contract requires it explicitly and
production backend resolution fails closed if it is missing or not
PostgreSQL. Phase 1 does not perform a deployment or connect to an external
database.

The application exposes `/health` for liveness and `/ready` for readiness. Put
Nginx or another controlled reverse proxy at the public boundary, terminate
TLS there, keep port 5000 private, and forward `X-Forwarded-Proto`,
`X-Forwarded-For`, and `X-Correlation-ID`.

## Container validation

After the protected environment, candidate metadata, trusted Gate 1 metadata,
and image are available, run the active-container validation command with an
absolute environment file outside the repository:

```text
python deployment/scripts/validate_production_runtime.py \
  --env-file /protected/sentinel-dna/production.env \
  --evidence-output /protected/sentinel-dna/evidence/production-runtime.json
```

The command validates Compose interpolation, starts PostgreSQL and Redis, runs
the migration job, starts Gunicorn, probes PostgreSQL-backed `/health` and
`/ready`, and fails if the selected backend is SQLite. Evidence contains only
statuses, response bodies from the health endpoints, the observed non-root UID,
and variable names; secret values and database URLs are never serialized. The
production Compose file sources `SENTINEL_DNA_SECRET_KEY` and
`POSTGRES_PASSWORD` from the operator environment into Docker secrets, then
passes only read-only secret-file paths to the application and migration
containers.

Before upgrades, create a SQLite backup without overwriting the primary file. Restore into a separate database location first and verify a known report, tenant authorization, governance metadata, `/health`, and `/ready`. For rollback, stop the application, deploy the previous known-good image/configuration, preserve the persistent volume, and restore the last validated backup only when necessary.

Never place secrets in source control or request logs. Review structured logs for correlation IDs and confirm that credentials, tokens, provider responses, authorization payloads, raw IOCs, and exception messages are absent.
