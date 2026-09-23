# Sentinel DNA External Staging Authority Package

**Package type:** documentation/evidence-only authority handoff
**Status:** pending external authority; not an authorization to operate

## 1. Purpose and scope

This package requests the minimum external authority inputs needed to unblock
the existing, fail-closed Sentinel DNA first-manager bootstrap for one
controlled evaluator staging run.

The run is:

- disposable, non-production Sentinel DNA staging;
- restricted to synthetic investigation data;
- explicitly `customer_data=false`;
- explicitly `credentials_or_tokens=false`;
- isolated from production, Gate 5 material, and production credentials.

This package does not authorize bootstrap by itself. The external authority
must independently establish and approve the required authority inputs.

## 2. Verified release identity

| Item | Value |
|---|---|
| Application commit | `e7473c98224234b205a7450ee83eb98efca584de` |
| Repository tree | `137d328cad1f9ae26b088c63e6674e09a675df49` |
| Staging image | `staging-app:e7473c98224234b205a7450ee83eb98efca584de` |
| Image digest | `sha256:99575058134c26e09c17e9bf1d7cbe7da0c2f42c125faeb548c00e20d2be365d` |
| Environment | `staging` / disposable non-production |

## 3. Exact authority inputs required

The external staging authority must independently supply or attest all of the
following, without placing secrets in this repository:

1. An approved disposable staging control tenant ID.
2. An active provider-verified requester identity bound to that tenant.
3. An active provider-verified reviewer identity bound to that tenant.
4. Requester and reviewer must be distinct actors.
5. Active canonical memberships for both identities in the control tenant,
   with the required requester and reviewer capabilities.
6. Active provider identity bindings for both identities, including provider,
   external subject, actor binding, and verification provenance.
7. The approved staging database target/configuration matching the reviewed
   contract:

   ```text
   SENTINEL_DNA_ENV=staging
   SENTINEL_DNA_STAGING_FIRST_ADMIN_BOOTSTRAP=1
   SENTINEL_DNA_STAGING_DEPLOYMENT_IDENTITY=sentinel-dna-staging-compose-v1
   SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION=disposable_staging
   SENTINEL_DNA_STAGING_DATABASE_TARGET_IDENTITY=postgresql://sentinel@postgres:5432/sentinel_dna
   DATABASE_URL=postgresql://sentinel@postgres:5432/sentinel_dna
   SENTINEL_DNA_STAGING_CONTROL_TENANT_ID=<approved-control-tenant-id>
   SENTINEL_DNA_STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAP_ENABLED=1
   ```

   Secret values, private keys, passwords, and secret-store contents are not
   requested in this package.

8. A generated approval ID from the staging bootstrap authorization service.
9. Its exact approval transaction ID.
10. Explicit authority to enable the staging-only migration 011 namespace.

The approval artifact must bind the operation, purpose, staging environment,
control tenant, target identity, fixed `soc_manager` role, database target
identity, requester actor, approval transaction ID, and expiry.

## 4. Controls already implemented by Sentinel DNA

The existing implementation provides:

- requester/reviewer separation;
- explicit requester/reviewer subject-to-key fingerprint binding in the signed
  trust manifest;
- provider principal validation and active identity provenance checks;
- tenant and canonical-membership binding;
- canonical approval-artifact hashing;
- approval transaction binding;
- one-time approval consumption in the provisioning transaction;
- fail-closed target, environment, database, role, expiry, and replay checks;
- immutable bootstrap consumption state;
- audit and provenance records with password/token exclusion.

The signed trust manifest must include `requester_subject` and
`reviewer_subject` alongside each role's key ID and public-key fingerprint.
Verification requires the payload subject, manifest subject, registered key ID,
resolved public key, fingerprint, and role signature to agree; requester and
reviewer subjects and keys must remain distinct. A key rotation therefore
requires a new explicitly bound manifest and does not rewrite historical
authorization identity.

Migration 011 adds only the staging bootstrap authorization and consumption
state. It does not create an authority source or bypass provider verification.

## 5. Explicitly not requested

This package does not request or authorize:

- any production tenant or production database;
- production credentials, secrets, or tokens;
- a private CA key;
- a Sentinel DNA application private key or secret key;
- customer data;
- unrestricted administrator access;
- public Internet exposure;
- access to Gate 5 evidence or checkouts;
- changes to application code, Docker stacks, PKI, or production.

## 6. Evidence already available

### PKI/TLS

Existing PKI/TLS was independently created on Laptop 2 with a root, issuing
CA, leaf chain, and CRL verification. This is infrastructure evidence only. It
does not establish identity-provider trust, canonical identity bindings,
requester/reviewer authority, or approval authority.

### PostgreSQL authority rehearsal

The disposable PostgreSQL authority rehearsal passed all of the following:

```text
requester separation
distinct reviewer
approval
manager provisioning
approval consumption
provenance preservation
password exclusion
```

Rehearsal evidence SHA-256:

```text
64C8537172EDD71CDD832D7EE9788848CF62A25447CC4187F0F1973E6935090E
```

The rehearsal manager exists only in the disposable rehearsal database and is
not a live staging authority.

### Current live-staging state

Based on the current verified staging state:

- staging is healthy;
- canonical tenants: `0`;
- privileged users: `0`;
- migration 011: not applied;
- staging bootstrap authorization records: none;
- evaluator provisioned: no.

## 7. Intended sequence after authority is supplied

```text
external authority bundle
  -> explicitly authorized migration 011
  -> one-time soc_manager bootstrap
  -> manager authentication and CSRF validation
  -> isolated evaluator provisioning
  -> one-time activation and MFA enrollment
  -> analyst-only workspace access
  -> predefined synthetic investigation
  -> evidence/provenance/report capture
  -> manager-controlled revocation and session invalidation
  -> final readiness record
```

The evaluator remains bounded by analyst role, isolated tenant, approved
scenario allowlist, expiry, MFA, CSRF, audit, provenance, and revocation
controls.

## 8. Next command, only after the authority bundle is received

This command is documented for the approved staging host only. It was **not**
executed while preparing this package. It may be executed only after the
external authority has supplied and independently approved the inputs in
Section 3, and after the external staging environment has been reviewed:

```sh
docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file deployment/staging/docker-compose.yml \
  run --rm --build migration
```

The external environment must set
`SENTINEL_DNA_STAGING_FIRST_PRIVILEGED_IDENTITY_BOOTSTRAP_ENABLED=1` in its
protected configuration. The one-time bootstrap script must then be run only
with the independently supplied tenant, approval ID, and approval transaction
ID. Password entry remains interactive and hidden; passwords and tokens must
not be placed in arguments, environment evidence, logs, or Git.

## 9. Authority attestation boundary

This package is a request and evidence handoff, not an authority grant. The
external staging authority remains responsible for independently verifying:

- tenant ownership and disposable classification;
- provider identity verification and distinctness;
- active canonical memberships and bindings;
- database target ownership and isolation;
- approval ID and transaction ID authenticity;
- authorization to enable migration 011.

Until that attestation is received, readiness remains **NO-GO / BLOCKED**.
