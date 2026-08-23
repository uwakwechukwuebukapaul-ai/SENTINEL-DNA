# Sentinel DNA Production Runbook

## Configuration contract

Only these values are protected secrets:

- `SENTINEL_DNA_SECRET_KEY`
- `POSTGRES_PASSWORD`

The release process derives these nonsecret values from the exact Git checkout:

- `SENTINEL_DNA_IMAGE_TAG` = full commit SHA
- `SENTINEL_DNA_IMAGE_REVISION` = nine-character commit prefix
- `SENTINEL_DNA_IMAGE_REVISION_FULL` = full commit SHA
- `SENTINEL_DNA_IMAGE_CREATED` = UTC build timestamp, or `SOURCE_DATE_EPOCH` when reproducibility is required

Never place secret values in Git, image labels, command output, generated reports, or logs. The Compose contract fails closed when secrets or immutable metadata are absent or inconsistent with HEAD.

## Protected local deployment

Create a protected, untracked `.env` from `.env.example` and provide only the two secret values. Do not add release metadata manually. Derive metadata into the current shell:

PowerShell:

```powershell
$metadata = python deployment/scripts/release_metadata.py --format json | ConvertFrom-Json
$env:SENTINEL_DNA_IMAGE_TAG = $metadata.SENTINEL_DNA_IMAGE_TAG
$env:SENTINEL_DNA_IMAGE_REVISION = $metadata.SENTINEL_DNA_IMAGE_REVISION
$env:SENTINEL_DNA_IMAGE_REVISION_FULL = $metadata.SENTINEL_DNA_IMAGE_REVISION_FULL
$env:SENTINEL_DNA_IMAGE_CREATED = $metadata.SENTINEL_DNA_IMAGE_CREATED
python deployment/scripts/validate_deployment_config.py --env-file .env
docker compose --env-file .env -f deployment/docker-compose.yml config --quiet
```

POSIX shell:

```sh
eval "$(python deployment/scripts/release_metadata.py --format shell)"
python deployment/scripts/validate_deployment_config.py --env-file .env
docker compose --env-file .env -f deployment/docker-compose.yml config --quiet
```

Use only `deployment/docker-compose.yml`. Recreate only the application service after configuration validation. Never use the root Compose file for production because it publishes port 5000.

## CI/CD deployment contract

The manual `deployment-contract` GitHub Actions workflow uses a protected `production` environment containing `SENTINEL_DNA_SECRET_KEY` and `POSTGRES_PASSWORD`. It derives the four release metadata values, validates the exact checkout, builds the immutable image, validates OCI provenance and the Compose contract, and runs deployment-adjacent tests.

The workflow intentionally does not assume a cloud host, registry, or remote deployment credential. An authorized operator must add the approved deployment adapter before enabling remote deployment. That adapter must deploy the immutable image and recreate only the application service unless an explicit infrastructure change is approved.

## Verification

Before opening traffic, verify the running container's image tag, digest, full revision label, non-root identity, `5000/tcp` with no host binding, and nginx's only public binding on port 80. Verify `/health` and `/ready` return 200 and unauthenticated execution visibility returns 401 `authentication_required`.

## Rotation and incident response

Rotate `SENTINEL_DNA_SECRET_KEY` and `POSTGRES_PASSWORD` through the protected environment or secret store only. Do not commit rotated values. If a secret may have been exposed, stop deployment, revoke and replace it in the protected store, review logs and CI artifacts, invalidate affected sessions where applicable, and redeploy an immutable image after validation.

## Rollback and emergency deployment

Rollback selects a previously certified full-SHA image and its matching configuration. Preserve the persistent volumes. Recreate only the application service, then repeat provenance, health, readiness, authentication, port-boundary, and log checks. Emergency deployment requires an authorized protected environment, a reviewed commit, immutable image provenance, and recorded operator evidence; it must not bypass secret validation or security controls.

The application remains one-worker and SQLite-authoritative. PostgreSQL and Redis remain internal infrastructure seams.
