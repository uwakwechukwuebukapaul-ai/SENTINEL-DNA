# Gate 5 Controlled Analyst Pilot Execution Runbook

## Operator decision

This runbook authorizes a controlled, non-production execution procedure only.
It does not authorize production access or claim production readiness. The
target decision is `READY_FOR_CONTROLLED_ANALYST_PILOT_EXECUTION` and remains
blocked until real authenticated evidence is captured, reviewed, and passes
all validators.

Use the existing Gate 4 readiness checklist and manual runbook as prerequisites:

- `deployment/staging/GATE4_ANALYST_PILOT_EXECUTION_READINESS_CHECKLIST.md`
- `deployment/staging/MANUAL_ANALYST_PILOT_RUNBOOK.md`
- `docs/gate5-controlled-analyst-pilot-execution-framework.md`

## Evidence handling rules

- Use only the certified staging origin and externally held trusted browser,
  bridge, runtime, image, TLS trust anchor, and custody services.
- Use exactly one approved synthetic tenant and one approved synthetic analyst;
  identities must be created or approved by the authorized operator process.
- Never put passwords, activation values, cookies, CSRF values, bearer tokens,
  session identifiers, database rows, customer data, or private runtime data
  in commands, logs, screenshots, Git, or evidence.
- Write evidence once to an append-only or independently hashable external
  custody location. Never overwrite an earlier record.
- Mark every unperformed observation `NOT_MEASURED`; never infer `PASS` from a
  configuration flag, HTTP 200, rehearsal, or test fixture.
- Rehearsal records must use `evidence_class: rehearsal` and must not be copied
  into the authenticated pilot evidence namespace.

## Before the pilot

1. Confirm the branch, reviewed commit, and clean worktree. Review the Gate 4
   artifact at `pilot-evidence/gate4/` and reconcile runtime, bridge, image,
   lockfile, manifest, and certified-origin identities with external custody.

2. On the approved operator host, run the authoritative Gate 4 check:

   ```powershell
   git status
   git log -5 --oneline
   node deployment/staging/scripts/check_controlled_pilot_readiness.mjs
   ```

   Require exactly `READY_FOR_ANALYST_PILOT` and all 13 checks `PASS`.

3. Verify the staging containers, health, and private TLS boundary:

   ```powershell
   docker compose ps
   curl.exe --cacert <approved-staging-ca.crt> https://sentinel-dna-staging:18443/health
   curl.exe --cacert <approved-staging-ca.crt> https://sentinel-dna-staging:18443/ready
   ```

   Verify only `127.0.0.1:18443->443/tcp` is published. Do not use `-k` as
   authoritative evidence and do not substitute a hostname, port, or listener.

4. Complete a fresh staging backup and isolated restore rehearsal before any
   pilot write. The evidence must identify the source deployment and schema,
   backup hash, immutable custody reference, isolated restore target, restore
   integrity, tenant separation, provenance preservation, and audit integrity.
   Do not copy the backup or database contents into the repository. If the
   current backup/restore record says `not_executed`, stop.

5. Confirm monitoring, escalation, evidence-custody, and recovery owners are
   available. Obtain the specific human approval for this non-production run
   through the approved custody process; do not create an approval artifact in
   Git.

6. Confirm the exact approved scope: one synthetic tenant, one analyst, bounded
   expiry, approved scenarios, and no production data. Generate a unique
   operator run ID without embedding credentials or session material.

## First-pilot execution sequence

1. Launch the approved trusted browser through the existing operator mechanism
   at the certified staging origin. Authentication must occur through the
   approved browser-auth bridge; no credential-bearing CLI or HTTP client is
   permitted.

2. Verify the manager role and active session. Exercise the documented missing
   CSRF denial before any protected state change and record only its opaque
   evidence reference and safe result.

3. Provision or activate only the approved synthetic scope when the authorized
   workflow requires it. Confirm the analyst identity, analyst role, expiry,
   and server-derived tenant context.

4. Have the analyst perform one approved, non-destructive synthetic
   investigation. Capture safe references for intake, workspace/result scope,
   provenance, human decision, and AI advisory-only behavior. Do not copy
   payloads or sensitive response bodies.

5. Execute the denial matrix and record direct observations:

   - known foreign-tenant resource: `403` or indistinguishable `404`, no leak;
   - manager/admin escalation and authorization management: denied;
   - direct database and shell/container access: denied;
   - destructive operation: denied and non-mutating.

6. Confirm the audit trail covers manager authentication, CSRF denial,
   provisioning/activation, investigation, workspace/result access, foreign
   denial, privileged denials, feedback, and provenance. Confirm each event has
   the required actor/role/tenant/action/correlation/time and integrity link.

7. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify subsequent login renewal, workspace reads, investigation reads, and
   feedback/action writes fail closed. Preserve only safe audit and custody
   references.

## Evidence assembly and validation

Create one externally held JSON record conforming to
`CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json` with:

- `evidence_class` exactly `authenticated_controlled_analyst_pilot`;
- real run ID, source commit, UTC start/completion times;
- one synthetic tenant and analyst identifier;
- direct gate observations and opaque custody references;
- audit/action/provenance references;
- revocation results and human decision;
- secret-free controls and deterministic SHA-256/custody metadata where used.

Run the focused validators against that external file:

```powershell
node deployment/staging/scripts/validate_authenticated_analyst_access.mjs <evidence-file>
node deployment/staging/scripts/validate_analyst_rbac.mjs <evidence-file>
node deployment/staging/scripts/validate_tenant_isolation.mjs <evidence-file>
node deployment/staging/scripts/validate_audit_trail.mjs <evidence-file>
node deployment/staging/scripts/validate_session_revocation.mjs <evidence-file>
node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs <evidence-file>
```

Every command must exit zero. Each validator fails closed with
`BLOCKED_WITH_REASON` and a safe field-level category for absent, malformed,
secret-bearing, rehearsal, stale, or unmeasured evidence. Do not rerun with a
bypass flag and do not edit evidence to turn a failed observation into `PASS`.

## After the pilot

- Hash and seal the evidence record through the approved external custody
  process; retain the custody receipt and provenance references, not secrets.
- Collect only approved pilot metrics: workflow completion, denial outcomes,
  audit completeness, provenance linkage, revocation latency, and operator
  feedback. Avoid customer data and sensitive payloads.
- Triage issues by severity and preserve the original evidence record.
- The release/security authority decides whether to repeat, extend, or close
  the controlled pilot. A passing Gate 5 pilot is not a production release.

## Stop and rollback

Stop immediately for public exposure, unexpected access, cross-tenant data,
missing audit/provenance, credential leakage, browser/provider drift,
backup/restore failure, unmeasured required gates, or any non-destructive test
that would mutate state.

1. Stop analyst activity and preserve the opaque run ID and UTC time.
2. Notify release/security and keep activation blocked.
3. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify post-revocation denial.
4. Preserve safe references and hashes in external custody; do not copy
   secrets or runtime artifacts into Git.
5. Tear down or revoke the staging runtime through its reviewed lifecycle.
6. Repair through the approved process and obtain fresh human approval before
   restarting. Any restart receives a new run ID and evidence record.
