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
approved enterprise secret authority (design target; not yet provisioned)
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
  --reviewed-sha <REVIEWED_RELEASE_SHA> `
  --expected-digest <VERIFIED_IMAGE_DIGEST> `
  --env-file <AUTHORIZED_PROTECTED_ENV_FILE> `
  --metadata-file C:\ProgramData\Sentinel-DNA\release\metadata.json `
  --release-manifest <VERIFIED_RELEASE_MANIFEST> `
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
operator authorization and preflight controls are complete, it first runs the
one-shot migration service from the pinned image:

```text
docker compose ... run --rm --no-build --no-deps migration
```

Only after that command succeeds does it recreate the application service with:

```text
docker compose ... up -d --no-build --no-deps app
```

PostgreSQL, Redis, and nginx are not recreated by the adapter. The migration
job mutates only the configured PostgreSQL schema and exits; it does not create
users, tenants, credentials, or default operational data. The Compose
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

## Release-boundary manifest

`deployment/scripts/release_manifest.py` produces a deterministic, non-secret
release evidence artifact outside the repository. It records the reviewed
commit SHA, Git tree identity, and SHA-256 plus Git blob identity for the
controller, validator, metadata helpers, Compose, nginx, Dockerfile, CI
workflow, release documentation, and required deployment/security tests. The
generated manifest is explicitly excluded from its own file set, so no
circular self-hash exists.

The release workflow must generate and verify this artifact from a clean
checkout before a release is considered reviewable. A manifest verifies source
provenance; it does not authorize Gate 1, provision secrets, or replace the
independent image-digest and trusted-metadata gates. Final release
certification must run verification with `--require-image` and an independently
verified digest for the same release SHA. The controller's existing reviewed
SHA check does not replace this artifact check; the release process must
complete manifest verification before any deployment validation is authorized,
so a working-tree controller is never accepted as a reviewed release by
process convention.

## Secret provisioning design (DESIGN ONLY)

No approved host-side provisioning mechanism currently exists. The target
enterprise custody model is:

```text
enterprise secret manager
  -> Windows machine identity and JIT authorization
  -> approved provisioning service with dual control
  -> atomic protected configuration/TLS materialization
  -> controlled_deploy.py validation
```

The future provider must enforce least privilege, operator approval and
separation of duties, auditable access, rotation and revocation, emergency
revocation, atomic replacement with rollback, parent-directory and file ACLs,
reparse-point rejection, TLS lifecycle controls, and zero secret-value
logging. Native secret injection should remain the longer-term migration path;
the flat protected environment file is a compatibility boundary, not a secret
authority. This section is a design proposal only and has not installed,
connected, or implemented a secret manager.

## Current integration gap

The existing GitHub Actions `deployment-contract` workflow validates and builds
under its protected `production` environment, publishes the exact authorized
candidate image to private GHCR, captures its immutable digest and non-secret
release evidence, but has no approved transport or deployment-host adapter. It
does not deploy containers. A future integration must be separately reviewed
before `--execute` is used from CI.
