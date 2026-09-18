# Staging First Privileged-Identity Bootstrap v1

This is a one-time, operator-only bootstrap for exactly one `soc_manager` in the externally approved staging control tenant. It composes `PrivilegedIdentityProvisioningService` with the dedicated `StagingBootstrapAuthorizationService`. It does not create an admin, add a web route, or use public registration.

The bootstrap requires the explicitly selected staging namespace migration overlay. Migration 011 adds only bootstrap consumption state to the existing approval workflow and does not create a second approval authority. It must be selected by the deployment migration service with:

```text
SENTINEL_DNA_STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAP_ENABLED=1
```

The owner-controlled external staging configuration contract must provide all of:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP=1
SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY=sentinel-dna-staging-compose-v1
SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION=disposable_staging
SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY=postgresql://sentinel@postgres:5432/sentinel_dna
DATABASE_URL=postgresql://sentinel@postgres:5432/sentinel_dna
SENTINEL_DNA_STAGING_CONTROL_TENANT_ID=<approved-control-tenant-id>
```

The database target identity is a password-free, exact deployment contract. The bootstrap also verifies PostgreSQL `current_database()` and `current_user`. Arbitrary PostgreSQL URLs, production URLs, password-bearing URLs, alternate hosts, alternate ports, and alternate database names are rejected.

The approval must be created through `StagingBootstrapAuthorizationService` by a verified requester and approved by a distinct verified reviewer. Its hashed artifact binds:

- operation and purpose;
- staging environment;
- control tenant;
- username and email;
- fixed `soc_manager` role;
- approved database target identity.

The bootstrap requires `--approval-id` and `--approval-transaction-id`; an opaque approval reference is not accepted. Approval verification and one-time consumption occur in the same PostgreSQL transaction as provisioning.

The PostgreSQL advisory transaction lock for the approved control tenant is acquired before preflight and is also acquired by normal privileged provisioning for the same tenant. It is held through provisioning, approval consumption, audit, and commit.

At the prompt, type exactly:

```text
BOOTSTRAP STAGING FIRST PRIVILEGED IDENTITY
```

The password and confirmation are entered with hidden prompts. They are never accepted as arguments or environment values and are not written to output, audit metadata, evidence, exceptions, or Git. Python string reassignment is not treated as secure memory erasure.

Example invocation:

```text
python deployment/staging/scripts/bootstrap_staging_first_privileged_identity.py --username soc-manager --email soc-manager@example.test --tenant-id <approved-control-tenant-id> --approval-id <approval-id> --approval-transaction-id <approval-transaction-id>
```

Do not run this procedure against the real staging database during development or testing. Do not use `deployment/scripts/provision_privileged_identity.py`.
