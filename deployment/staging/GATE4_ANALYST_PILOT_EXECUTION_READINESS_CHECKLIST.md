# Gate 4 Controlled Analyst Pilot Execution Readiness Checklist

This checklist prepares the first authenticated, non-production Sentinel DNA
analyst pilot. It does not authorize production release, create credentials,
issue a public endpoint, or convert unmeasured evidence into `PASS`.

## Current state

| Item | Current state | Evidence or action |
| --- | --- | --- |
| Branch | `gate4-controlled-analyst-pilot` | Verify at execution time |
| Handoff commit | `fa8aa1fef3010beb00dff84bd7f76fec4e0fbaaf` | Working tree was clean at review |
| Gate 4 infrastructure readiness | `READY_FOR_ANALYST_PILOT` | 13/13 readiness checks pass |
| Provider/runtime/bridge custody | PASS | Reconcile again immediately before execution |
| Certified origin | PASS | Reconfirm exact private origin and TLS on the operator host |
| Authenticated analyst gates | `NOT_MEASURED` | Must be directly observed during this pilot |
| Current staging Docker CLI access | `NOT_MEASURED` in this shell | `docker compose ps` must pass on the approved operator host |
| Production readiness | NOT CLAIMED | Requires a separate production gate |

The authoritative current readiness reference is
`pilot-evidence/gate4/gate4-controlled-pilot-readiness-20260902.json`. The
historical blocked pilot artifacts remain retained and must not be rewritten.

## Hard-stop rules

Stop before authentication if any item is `FAIL`, `BLOCKED`, stale, or
`NOT_MEASURED` where this checklist requires direct observation. Do not use:

- production data, production credentials, or a production database;
- a fixture, mock, fake runtime, standalone browser, CDP/debugging port, or
  direct credential-bearing HTTP client;
- an alternate hostname, port, listener, URL, or trust bypass;
- copied passwords, cookies, CSRF values, activation tokens, or sessions in
  command arguments, logs, source control, screenshots, or evidence.

## 1. Operator and environment preflight

- [ ] Confirm the branch is `gate4-controlled-analyst-pilot`.
- [ ] Confirm the reviewed handoff commit and a clean working tree.
- [ ] Confirm the non-secret operator configuration references the externally
      held runtime, browser-auth bridge, activation manifest, image digest, and
      staging TLS trust anchor.
- [ ] Confirm no repository path is being used for external runtime bundles,
      private keys, credentials, browser sessions, or database backups.
- [ ] Run the configuration dry run and provider verification; record only
      safe statuses, identities, and digests.
- [ ] Run `node deployment/staging/scripts/check_controlled_pilot_readiness.mjs`
      and require exactly `READY_FOR_ANALYST_PILOT` with every check `PASS`.
- [ ] Run `docker compose ps` on the approved operator host and record the
      isolated staging project and container health.
- [ ] Confirm only `127.0.0.1:18443->443/tcp` is published. Stop for any
      wildcard, LAN, public, management, database, Redis, or application
      listener.
- [ ] Confirm `/health` and `/ready` return HTTP 200 through the exact
      certified origin using the approved CA. The `curl -k` diagnostic is not
      sufficient evidence for TLS trust.
- [ ] Confirm the active image digest and external manifest/runtime/bridge
      digests are unchanged from the approved custody record.

## 2. Backup and restore gate

### Current evidence assessment

The PostgreSQL rehearsal report at external custody records migration,
transaction rollback, provenance, tenant, and audit checks, but explicitly
records `backup_restore_rehearsal: not_executed`. The SQLite recovery utilities
and disposable fixtures are validation tooling, not proof of a live staging
backup. Therefore current staging backup/restore readiness is `BLOCKED` until
the operator supplies fresh deployment-specific evidence.

### Required evidence before pilot mutation

- [ ] Identify the current staging database engine, source boundary, backup
      owner, restore owner, retention policy, and recovery contact.
- [ ] Create one immutable backup outside the repository, without overwriting
      an existing artifact or the live database.
- [ ] Record only non-secret metadata: UTC time, source deployment/image
      identity, schema/migration version, artifact size, artifact SHA-256, and
      manifest/reference location.
- [ ] Validate the backup artifact and manifest against the exact source,
      including database integrity, schema identity, table inventory/counts,
      and content digest where the approved validator requires it.
- [ ] Restore to a new isolated target. Never restore over the source or the
      backup input.
- [ ] Verify restored integrity, schema, record counts, provenance columns,
      tenant scope, and append-only audit integrity.
- [ ] Verify the restored target preserves tenant separation and audit hashes;
      record non-secret references rather than rows or payloads.
- [ ] Have the recovery owner review the artifact and record approval through
      the approved custody process. Do not manufacture an approval in Git.
- [ ] Keep backup and restore artifacts outside Git; commit only a safe
      evidence reference if release custody requires one.

No pilot account or investigation write should occur until this gate is
`PASS`, unless the release/security owner explicitly records a blocked stop and
does not proceed.

## 3. Tenant isolation evidence gate

The readiness flag `SENTINEL_DNA_TENANT_ISOLATION_ENABLED=1` is not behavioral
proof. Historical authenticated pilot evidence has `tenant_isolation` as
`NOT_MEASURED`; the bounded PostgreSQL rehearsal is not a substitute for the
deployed application test.

- [ ] Obtain approval for exactly one synthetic pilot tenant and one synthetic
      analyst account, with an explicit expiry.
- [ ] Record the pilot tenant and analyst identifiers only after creation and
      only as non-secret identifiers.
- [ ] Confirm the analyst identity, role, authorization, and server-derived
      tenant context.
- [ ] Read the analyst workspace and investigation result; confirm every
      returned object is scoped to the pilot tenant.
- [ ] Use an approved known foreign-tenant synthetic resource and require the
      documented `403` or indistinguishable `404` denial.
- [ ] Confirm the denied request returns no foreign tenant identifier, record,
      evidence, audit content, or changed tenant context.
- [ ] Verify analyst attempts against admin, authorization-management,
      provisioning, database, shell/container, runtime-management, and
      destructive surfaces are denied and non-mutating.
- [ ] Record endpoint path classification, HTTP result, tenant scope, and
      non-secret observation reference for each denial.

## 4. Audit and provenance evidence gate

The prior `MONITOR-PILOT-001` artifact proves bounded synthetic monitoring
ownership only. It does not prove an authenticated analyst audit trail. A
healthy endpoint, a readiness flag, or HTTP 200 alone is insufficient.

- [ ] Confirm the deployed staging service is emitting audit events before the
      first authenticated action.
- [ ] For manager authentication, CSRF denial, provisioning, analyst
      activation, investigation intake, workspace access, foreign-tenant
      denial, privileged-surface denials, feedback, revocation, deactivation,
      and session invalidation, record a non-secret audit reference.
- [ ] Confirm each event includes actor/role, tenant scope, action or denial,
      correlation reference, UTC timestamp, and integrity/provenance linkage
      as required by the deployed contract.
- [ ] Confirm investigation evidence provenance links the synthetic input,
      canonical execution path, result, and tenant without serializing
      sensitive payloads.
- [ ] Confirm audit and provenance reads cannot cross tenant boundaries.
- [ ] Confirm AI recommendation and human conclusion remain separate and the
      AI result is advisory-only with explicit human review required.
- [ ] Confirm the evidence sink is append-only or independently hashable and
      the evidence file contains no credentials, tokens, cookies, sessions, or
      customer data.

## 5. Human approval and pilot scope

- [ ] Security/release authority approves this specific non-production run.
- [ ] Manager identity is approved through the protected operator process.
- [ ] Exactly one synthetic tenant and one synthetic analyst are in scope.
- [ ] Approved scenarios and denial paths are written into the operator run
      record before authentication.
- [ ] No analyst URL is issued during preparation. Any later endpoint remains
      private and origin-scoped.
- [ ] Operator, monitoring, escalation, and evidence-custody owners confirm
      availability for the run.

## 6. Exact first-pilot operator sequence

Run these steps in order. Preserve command output only when it is non-secret.

1. Set the approved external operator environment and confirm configuration
   without printing values.
2. Run:

   ```powershell
   git status
   git log -5 --oneline
   node deployment/staging/scripts/check_controlled_pilot_readiness.mjs
   ```

   Require `READY_FOR_ANALYST_PILOT` and all checks `PASS`.
3. Run `docker compose ps` and verify the isolated project, health, networks,
   and loopback-only edge publication.
4. Verify the private TLS `/health` and `/ready` endpoints with the approved
   trust anchor. Do not use `-k` as the authoritative check.
5. Complete the fresh staging backup and isolated restore gate. Stop if the
   artifact, manifest, restore, tenant-preservation, or audit-integrity check
   is not `PASS`.
6. Obtain and record human approval for the single synthetic tenant and single
   analyst account. Do not place credentials or activation values in the run
   record.
7. Start a unique non-secret run ID and UTC timestamp.
8. Launch the approved runner with only the run ID:

   ```powershell
   node deployment/staging/scripts/run_controlled_analyst_pilot.mjs <operator-run-id>
   ```

   The runner must obtain credentials only through the approved browser-auth
   capability. Do not add credential arguments or provisioning secrets.
9. Verify manager role and session, then verify the missing-CSRF denial before
   any protected write.
10. Provision only the approved synthetic pilot scope, if provisioning is
    authorized for this run; otherwise record `NOT_PERFORMED`.
11. Have the analyst activate through the protected channel and execute one
    approved synthetic investigation.
12. Execute tenant-isolation, provenance, AI advisory-only, denial-boundary,
    and audit checks. Record direct observations and references.
13. Revoke authorization, deactivate the analyst, invalidate sessions, and
    verify post-revocation denial for login renewal, workspace reads,
    investigation reads, and feedback/action writes.
14. Create one new append-only evidence record under approved custody. Mark
    every unperformed item `NOT_MEASURED`; never infer `PASS`.
15. After human evidence review, run:

    ```powershell
    node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs <evidence-file>
    ```

    Require exactly `READY_FOR_CONTROLLED_ANALYST_PILOT` before considering
    the pilot complete. This result is not production approval.

16. Run the Gate 5 focused validators against the same externally held
    authenticated pilot evidence record. Every command must exit zero:

    ```powershell
    node deployment/staging/scripts/validate_authenticated_analyst_access.mjs <evidence-file>
    node deployment/staging/scripts/validate_analyst_rbac.mjs <evidence-file>
    node deployment/staging/scripts/validate_tenant_isolation.mjs <evidence-file>
    node deployment/staging/scripts/validate_audit_trail.mjs <evidence-file>
    node deployment/staging/scripts/validate_session_revocation.mjs <evidence-file>
    ```

    These validators accept only `evidence_class:
    authenticated_controlled_analyst_pilot`; rehearsal and Gate 4
    infrastructure evidence remain separate and are rejected.

## 7. Stop and rollback conditions

Stop immediately for unexpected access, cross-tenant data, missing audit or
provenance linkage, credential leakage, runtime or browser-auth anomaly,
public exposure, backup/restore failure, evidence contamination, or any
unmeasured required gate.

1. Stop pilot activity and preserve only the non-secret run ID and UTC time.
2. Notify the release/security owner and keep activation blocked.
3. Revoke authorization, deactivate the analyst, and invalidate sessions.
4. Verify post-revocation denial and preserve safe audit/evidence hashes.
5. Tear down or revoke the external runtime through its reviewed lifecycle.
6. Preserve the backup and evidence custody references without copying secrets.
7. Repair through the approved process, rerun all gates, and obtain fresh human
   approval before restarting.

## 8. Exit decision

The first pilot is complete only when the manual validator returns
`READY_FOR_CONTROLLED_ANALYST_PILOT`, all required authenticated gates are
directly evidenced, revocation is verified, and human release authority has
reviewed the result. Otherwise the decision remains `BLOCKED_WITH_REASON` or
`NOT_MEASURED`.

This checklist prepares a controlled analyst pilot only. It does not claim
production readiness.
