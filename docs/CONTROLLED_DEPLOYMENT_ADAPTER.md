# Controlled Production Deployment Adapter V1

`deployment/scripts/controlled_deploy.py` is the fail-closed deployment boundary
for the production Compose lane. It does not create secrets or fetch them from
GitHub. An authorized secret/configuration provider must first materialize a
protected environment file outside the repository. The adapter then validates
that file, the release image, the deployment-owned trusted metadata, and the
Compose topology in memory.

## Custody boundary

The intended custody chain is:

```text
protected GitHub production authority
  -> approved operator/provider materialization
  -> protected Windows environment file
  -> controlled_deploy.py
  -> deployment/docker-compose.yml
```

The repository `.env` and `.env.example` are rejected as deployment authority.
The adapter never prints, serializes, or includes the values of
`SENTINEL_DNA_SECRET_KEY` or `POSTGRES_PASSWORD` in evidence. The adapter does
not implement GitHub transport, SSH, WinRM, or secret rotation; those remain an
authorized infrastructure integration responsibility.

The protected environment file, its parent directory, the trusted metadata
file, its parent directory, and the TLS directory must be regular non-reparse
paths outside the repository. On Windows, SYSTEM and Administrators must have
full control; non-privileged principals must not have write, create, delete, or
replace rights. Any privileged deny entry, unsafe parent ACL, symlink, or
reparse point fails closed. The Compose metadata and TLS mounts must remain
read-only.

## Validation-only invocation

Use an authorized protected environment path supplied by the deployment
operator. Do not substitute the repository `.env`:

```powershell
python deployment/scripts/controlled_deploy.py `
  --reviewed-sha 4ccd97552723b7171e9a29bbfde415ba054bd3b0 `
  --expected-digest sha256:9a212a06eed455a43675c75cf1324827b33bc44070c6f0ccd7d5f9df0be4b91d `
  --env-file <AUTHORIZED_PROTECTED_ENV_FILE> `
  --metadata-file C:\ProgramData\Sentinel-DNA\release\metadata.json `
  --docker-executable C:\Users\<operator>\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe `
  --dry-run
```

`--dry-run` and `--validate-only` perform no deployment, restart, metadata
write, database mutation, or credential mutation. They independently verify
the current Git SHA, local image digest and OCI labels, exact trusted metadata,
Windows ACLs, and the rendered Compose topology. Command output is limited to
safe release/evidence fields and static failure categories.

## Deployment boundary

The explicit `--execute` mode is not part of release validation. After all
operator authorization and preflight controls are complete, it recreates only
the application service with:

```text
docker compose ... up -d --no-build --no-deps app
```

PostgreSQL, Redis, and nginx are not recreated by the adapter. The Compose
contract requires the application, PostgreSQL, and Redis to remain internal;
nginx alone publishes ports 80 and 443. Runtime verification confirms the
running application digest and read-only trusted metadata mount. Immediately
before execution the image is re-inspected and the app service is pinned to
the verified digest through a temporary Compose override, reducing mutable-tag
TOCTOU risk. Temporary files are outside the repository and removed after the
command.

## Evidence

Optional `--evidence-output` writes only safe JSON fields: release SHA, image
identity, OCI provenance, validation results, mode, and mutation status. The
output path must be treated as a deployment evidence artifact and must not be
used for environment configuration.

## Current integration gap

The existing GitHub Actions `deployment-contract` workflow validates and builds
under its protected `production` environment, but it has no approved transport
or deployment-host adapter. It does not materialize a local environment file,
prepare the trusted host artifact, push an image, or deploy containers. A future
integration must be separately reviewed before `--execute` is used from CI.
