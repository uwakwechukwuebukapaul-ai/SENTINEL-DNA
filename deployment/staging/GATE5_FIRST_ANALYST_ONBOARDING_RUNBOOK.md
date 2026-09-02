# Gate 5 First Analyst Onboarding Runbook

## Purpose and status

This runbook prepares the first real authenticated analyst login through
Tailscale private access. It is limited to the existing staging
deployment and does not modify production architecture. Current status remains
`READY_FOR_ANALYST_PILOT`; it must not be changed to a completed-pilot status
until real evidence is captured and reviewed.

## Preconditions

Do not start authentication until all of these are complete:

- Gate 4 readiness returns `READY_FOR_ANALYST_PILOT` with 13/13 checks PASS.
- Current provider, runtime, browser bridge, image, manifest, TLS, and lockfile
  identities match external custody.
- Fresh staging backup and isolated restore evidence is PASS.
- Tailscale private overlay, least-privilege policy, enrolled analyst device,
  MFA, raw TCP forwarding, and expiry are approved.
- The exact origin is reachable from the enrolled analyst device with approved
  CA/SNI validation.
- One analyst, one synthetic tenant, one scenario set, and rollback owners are
  approved.
- No credentials, tokens, cookies, tunnel secrets, or private keys are in the
  repository or evidence workspace.

Any missing precondition is `BLOCKED_WITH_REASON`; do not continue.

## 1. Open the run

1. Create a unique external run ID and UTC start time.
2. Open an append-only record using
   `GATE5_ANALYST_ACCESS_EVIDENCE.schema.json` with:
   `evidence_class: remote_access_preflight` and `status: NOT_EXECUTED`.
3. Bind the external Tailscale policy, node/device, forwarding, and custody references
   to the run without copying their secret values.
4. Review the existing Gate 4 evidence and retain historical blocked records;
   do not overwrite them.

## 2. Validate private access before login

Run on the approved operator host, then on the enrolled analyst device:

```powershell
node deployment/staging/scripts/check_controlled_pilot_readiness.mjs
docker compose -f deployment/staging/docker-compose.yml ps
docker compose -f deployment/staging/docker-compose.yml port edge 443
Resolve-DnsName uwakwe-desktop.taile388cc.ts.net
Test-NetConnection uwakwe-desktop.taile388cc.ts.net -Port 443
curl.exe --cacert <approved-staging-ca.crt> https://uwakwe-desktop.taile388cc.ts.net/health
curl.exe --cacert <approved-staging-ca.crt> https://uwakwe-desktop.taile388cc.ts.net/ready
```

Confirm:

- URL, SNI, Host, and Origin remain `uwakwe-desktop.taile388cc.ts.net`;
- certificate verification succeeds with the approved CA;
- there is no redirect to a public or alternate hostname;
- the edge remains `127.0.0.1:18443->443/tcp`;
- database, Redis, Docker, SSH, shell, management, and production routes are
  unavailable;
- Tailscale network evidence and Sentinel health evidence are distinct.

If Tailscale Serve is configured for HTTPS/TLS termination, `https+insecure`,
Funnel, a subnet route, or any destination other than
`tcp://127.0.0.1:18443`, stop. Use the raw TCP forwarding path so Sentinel DNA
continues to validate its own certificate and `sentinel-dna-staging` SNI.

## 3. Manager setup

1. Manager opens the exact certified origin through the approved trusted
   browser/provider.
2. Manager authenticates only through the protected browser-auth flow.
3. Verify manager identity, role, tenant context, active session, and secure
   cookie behavior through the application.
4. Exercise the documented missing-CSRF denial before any protected write.
5. Provision only the approved synthetic tenant and analyst through the
   protected manager workflow, if provisioning is included in the approval.
6. Record only opaque identity, tenant, authorization, expiry, audit, and
   provenance references.

Do not put passwords, activation values, cookies, CSRF values, bearer tokens,
or session identifiers in commands, logs, tickets, screenshots, or evidence.

## 4. First analyst login

1. Confirm the analyst has been approved externally and the remote policy Allow
   rule matches only that identity.
2. Analyst uses the approved enrolled device and opens exactly
   `https://uwakwe-desktop.taile388cc.ts.net`.
3. Analyst authenticates through the approved channel; the operator does not
   request or handle the analyst's password or one-time activation value.
4. Verify and record safe references for:
   - authenticated analyst identity;
   - role exactly `analyst`;
   - server-derived tenant context;
   - authorization scope and UTC expiry;
   - successful access to the bounded workspace.
5. Do not mark the authenticated pilot evidence `VERIFIED` from login alone.

## 5. Controlled analyst actions

1. Analyst performs one approved, non-destructive synthetic investigation.
2. Verify the investigation, workspace, result, evidence, and feedback remain
   tenant-scoped.
3. Verify RBAC denials for admin escalation, authorization management,
   provisioning, database, shell/container, runtime-management, secrets,
   metrics, and destructive surfaces.
4. Verify a known foreign-tenant resource returns the documented `403` or
   indistinguishable `404` with no foreign identifier, payload, audit content,
   provenance, or tenant-context leakage.
5. Verify AI output remains advisory-only and separate from the human analyst
   conclusion.

Record direct observations, UTC timestamps, response classifications, and
opaque evidence references. Do not copy sensitive response bodies.

## 6. Audit and provenance capture

Capture safe references for manager authentication, CSRF denial, provisioning,
activation, analyst login, investigation intake, workspace/result access,
foreign-tenant denial, every privileged denial, feedback, AI advisory-only
handling, authorization revocation, deactivation, and session invalidation.

For each reference, verify the deployed audit contract provides actor, role,
tenant, action/denial, correlation ID, UTC time, and integrity linkage. Verify
provenance links the synthetic input, execution path, result, tenant, and
human/AI decision separation. Tailscale network evidence may corroborate private
network entry but does not replace Sentinel DNA application audit events.

## 7. Revocation and closeout

1. Revoke the analyst authorization with an externally recorded reason.
2. Deactivate the analyst and invalidate all active sessions.
3. Verify login renewal, workspace reads, investigation reads, and feedback or
   action writes fail closed from the analyst device.
4. Disable or narrow the Tailscale grant/ACL, Serve listener, and analyst
   device access.
5. Seal the external evidence record and record its SHA-256/custody receipt.
6. Mark evidence `VERIFIED` only after human review and complete direct
   observations. Otherwise retain `NOT_MEASURED` or `BLOCKED_WITH_REASON`.

## 8. Final validation commands

Run against the externally held authenticated pilot evidence file:

```powershell
node deployment/staging/scripts/validate_authenticated_analyst_access.mjs <evidence-file>
node deployment/staging/scripts/validate_analyst_rbac.mjs <evidence-file>
node deployment/staging/scripts/validate_tenant_isolation.mjs <evidence-file>
node deployment/staging/scripts/validate_audit_trail.mjs <evidence-file>
node deployment/staging/scripts/validate_session_revocation.mjs <evidence-file>
node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs <evidence-file>
```

Every command must exit zero before the controlled pilot is considered
complete. Missing, rehearsal-class, secret-bearing, stale, or unmeasured
evidence remains blocked. These commands inspect evidence only; they do not
authenticate, provision, revoke, or mutate Sentinel DNA.
