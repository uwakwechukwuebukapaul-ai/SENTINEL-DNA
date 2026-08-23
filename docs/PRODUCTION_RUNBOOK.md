# Sentinel DNA Production Runbook

## Configuration contract

Only these values are protected secrets:

- `SENTINEL_DNA_SECRET_KEY`
- `POSTGRES_PASSWORD`

The release process derives these nonsecret values from the exact Git checkout:

- `SENTINEL_DNA_IMAGE_TAG` = full commit SHA
- `SENTINEL_DNA_IMAGE_REVISION` = nine-character commit prefix
- `SENTINEL_DNA_IMAGE_REVISION_FULL` = full commit SHA
- `SENTINEL_DNA_IMAGE_DIGEST` = immutable deployed image digest
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

## Gate 1 synthetic identity provisioning

Gate 1 requires two authenticated, isolated synthetic identities. The checked-in
operator command provisions exactly `Gate1 Tenant A` and `Gate1 Tenant B` through
the existing authentication, canonical authority, password-hashing, and audit
services. It is deliberately out-of-band: it is not an HTTP route, is not called
by application startup, and is not available to ordinary application users.

The command must run only against the exact reviewed production image and only
when all of the following are true:

- the operator is using an authorized protected deployment environment;
- `SENTINEL_DNA_GATE1_PROVISIONING=1` is set explicitly for that command;
- `SENTINEL_DNA_ENV=production` is set;
- `SENTINEL_DNA_IMAGE_REVISION_FULL` matches the full reviewed Git revision;
- `SENTINEL_DNA_IMAGE_DIGEST` matches the digest in the protected, read-only
  Gate 1 release metadata file;
- `SENTINEL_DNA_GATE1_TRUSTED_METADATA_PATH` points to that protected file. The
  file contains only nonsecret `release_sha` and `image_digest` fields and is
  established independently by the reviewed image release process;
- `SENTINEL_DNA_SECRET_KEY` and `SENTINEL_DNA_DB_PATH` are available through
  protected configuration; and
- the command is run interactively so password prompts are hidden.

The passwords are never command-line arguments, printed, logged, returned, or
stored in the repository. The operator must choose them through the hidden
`getpass` prompts; do not place them in `.env`, shell history, CI output, or
documentation. The command uses the application database path and canonical
services; it does not use ad-hoc SQL, test email/SMS providers, legacy JSON
registration compatibility, or an authentication bypass.

After a new reviewed image containing the command is built, an authorized
operator may provision the identities interactively from PowerShell. The
revision value below is nonsecret release metadata:

```powershell
$revision = (git rev-parse HEAD).Trim()
$env:SENTINEL_DNA_GATE1_PROVISIONING = "1"
$env:SENTINEL_DNA_ENV = "production"
$env:SENTINEL_DNA_IMAGE_REVISION_FULL = $revision
docker compose --env-file .env -f deployment/docker-compose.yml exec `
  -e SENTINEL_DNA_GATE1_PROVISIONING=1 `
  -e SENTINEL_DNA_ENV=production `
  -e SENTINEL_DNA_IMAGE_REVISION_FULL=$revision `
  app python deployment/scripts/provision_gate1_synthetic_identities.py provision `
  --expected-revision $revision
```

The command prints only lane, synthetic tenant, synthetic actor, user identifier,
and state. A successful first run reports `provisioned`; a safe repeat reports
`already_provisioned` and does not prompt for passwords. Any partial or conflicting
state fails closed and requires operator review. Do not invoke this command
against an image or checkout whose full revision has not been independently
verified.

After Gate 1 evidence is collected, the same guarded command can expire only the
two identities it created:

```powershell
docker compose --env-file .env -f deployment/docker-compose.yml exec `
  -e SENTINEL_DNA_GATE1_PROVISIONING=1 `
  -e SENTINEL_DNA_ENV=production `
  -e SENTINEL_DNA_IMAGE_REVISION_FULL=$revision `
  app python deployment/scripts/provision_gate1_synthetic_identities.py cleanup `
  --expected-revision $revision
```

Cleanup deactivates the marked synthetic users, memberships, identities, and
tenants and records audit events. It refuses partial state or any identifier that
does not exactly match the reserved synthetic marker. It does not perform broad
deletion and does not remove persistent volumes. Never expose this operation as
an HTTP endpoint or enable test providers, development mode, debug mode, or
`AUTH_LEGACY_JSON_COMPAT` to replace it.

### Guarded recovery after cleanup

`cleanup -> ordinary provision` is unsupported. Ordinary `provision` continues
to fail closed when any retained Gate 1 record exists, including a complete
inactive graph. A future reviewed release may use the separate
`rotate` action to perform:

`ABSENT -> provision -> ACTIVE_COMPLETE -> cleanup -> INACTIVE_COMPLETE -> rotate -> ACTIVE_COMPLETE`

Rotation requires every selected lane to contain exactly its reserved inactive
user, password identity, canonical identity, membership, and tenant. All four
records must be inactive, the membership role must remain `analyst`, the graph
must remain bound to the reserved tenant and actor identifiers, and no duplicate,
cross-tenant, provider, partial, or mixed state may exist. Any other state is
rejected before password prompts.

The trusted release metadata file is not operator-entered release metadata. It
must be provisioned by the reviewed release process, remain a regular
non-symlink file, and not be writable by group or other users. Missing,
malformed, mismatched, or unavailable metadata fails closed before any state
inspection or password prompt.

Rotation is additionally gated by `SENTINEL_DNA_GATE1_ROTATION=1` alongside the
existing provisioning, production, full-release, protected-configuration, and
database-path guards. It is operator-only and must run interactively. The command
uses hidden `getpass` prompts for replacement passwords; passwords are never
arguments, environment values, logs, audit metadata, results, or exceptions.

On a reviewed release, select one lane with `--lane A` or `--lane B`, or select
both by omitting `--lane`. A single-lane operation never expands to the other
lane. Both-lane rotation is one transaction: password hashing, persistent-session
revocation, session-epoch advancement, reactivation, and one safe
`GATE1_SYNTHETIC_IDENTITY_ROTATED` audit event per lane commit together or roll
back together. The rotation command prints only safe lane, tenant, actor, user,
and result-state metadata.

The reviewed release adds the additive `users.session_version` epoch with a
default of zero. Existing signed sessions remain compatible at epoch zero;
rotation advances the reserved user epoch and the request boundary rejects older
signed sessions. Persistent sessions are revoked in the same transaction.

The current certified release remains cleanup-terminal and does not support this
rotation action. Do not run the rotation command until its reviewed release SHA,
immutable image digest, operator authorization, and runtime certification have
been independently verified.

## Privileged runtime identity bootstrap

Gate 1 audit-read validation requires an existing tenant-bound `admin` or
`soc_manager` identity. The checked-in privileged bootstrap command is an
operator-only deployment action for the initial or recovery identity. It is not
an HTTP endpoint, is not available to application users, and never changes an
existing account.

The command requires all of the following:

- an authorized operator using the protected deployment environment;
- `SENTINEL_DNA_PRIVILEGED_BOOTSTRAP=1` explicitly set for that command;
- `SENTINEL_DNA_ENV=production`;
- `SENTINEL_DNA_IMAGE_REVISION_FULL` matching the exact reviewed release;
- `SENTINEL_DNA_SECURE_COOKIES=1`;
- protected `SENTINEL_DNA_SECRET_KEY` and `SENTINEL_DNA_DB_PATH`; and
- an already-existing active canonical tenant.

Only `admin` and `soc_manager` are accepted. The command does not create a
tenant, does not accept a password argument, does not reset or overwrite an
existing username, and records a safe `PRIVILEGED_IDENTITY_PROVISIONED` audit
event in the same transaction as the user, canonical identity, and membership.
The operator enters the password and confirmation through hidden prompts.

From an attached PowerShell terminal, after independently verifying the exact
reviewed image and release metadata:

```powershell
$revision = (git rev-parse HEAD).Trim()
$env:SENTINEL_DNA_PRIVILEGED_BOOTSTRAP = "1"
$env:SENTINEL_DNA_ENV = "production"
$env:SENTINEL_DNA_IMAGE_REVISION_FULL = $revision
$env:SENTINEL_DNA_SECURE_COOKIES = "1"

docker compose --env-file .env -f deployment/docker-compose.yml exec `
  -e SENTINEL_DNA_PRIVILEGED_BOOTSTRAP=1 `
  -e SENTINEL_DNA_ENV=production `
  -e SENTINEL_DNA_IMAGE_REVISION_FULL=$revision `
  -e SENTINEL_DNA_SECURE_COOKIES=1 `
  app python deployment/scripts/provision_privileged_identity.py `
  --username <operator-selected-username> `
  --email <operator-selected-email> `
  --tenant <existing-canonical-tenant-id> `
  --role admin `
  --expected-revision $revision
```

Use `--role soc_manager` when that is the approved role. The command prints
only nonsecret identity metadata after success. A duplicate username or invalid
tenant fails closed. Never put the password in `.env`, PowerShell history,
command arguments, logs, or reports.

After successful bootstrap, authenticate the identity through the HTTPS Gate 1
procedure using a fresh local `Read-Host -AsSecureString` prompt and validate
`GET /api/admin/audit`. Analyst identities must remain denied. This bootstrap
CLI is a bounded initial/recovery mechanism; enterprise deployments should
progress toward Enterprise IdP/OIDC and SCIM or equivalent administrative
provisioning while retaining the CLI for controlled break-glass recovery.

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
