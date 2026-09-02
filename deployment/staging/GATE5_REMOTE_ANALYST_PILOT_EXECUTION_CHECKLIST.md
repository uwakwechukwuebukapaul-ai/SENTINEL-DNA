# Gate 5 Remote Analyst Pilot Execution Checklist

This checklist prepares one controlled, non-production remote analyst pilot.
It does not authorize production deployment and does not create pilot evidence.
Every unchecked, stale, or `NOT_MEASURED` item is a stop condition.

Target decision:

`READY_FOR_CONTROLLED_ANALYST_PILOT_EXECUTION`

## Current state

- Reviewed base commit: `fa8aa1fef3010beb00dff84bd7f76fec4e0fbaaf`.
- Gate 4 infrastructure: `READY_FOR_ANALYST_PILOT`, 13/13 checks PASS.
- Gate 5 authenticated pilot evidence: not executed.
- Historical analyst records: retained as blocked/not measured; do not rewrite.
- Production readiness: not claimed.

## Architecture recommendation

Use the selected Tailscale private overlay to the existing staging host.
Configure a deny-by-default Tailscale grant/ACL for the single approved
analyst, allowing only TCP `443` to the tagged staging node. Use raw TCP
Tailscale Serve forwarding to `tcp://127.0.0.1:18443`, so the existing
Sentinel DNA TLS edge and exact MagicDNS origin remain
authoritative. Do not add a subnet router, exit node, Tailscale SSH rule, or
public Funnel route.

Do not use a normal public-hostname Tunnel route for this pilot. That mode
creates a public DNS hostname and changes the browser-visible origin. Do not
accept that change by adding an alternate origin to the application or
validators.

Cloudflare One private access is paused and must not be used for this run. A
separately approved narrowly routed WireGuard overlay is also not selected for
this run. Any future alternate path requires a reopened architecture decision
and fresh external approval. Do not expose SSH, Docker, PostgreSQL, Redis,
management, or debug ports to the analyst.

PythonAnywhere is not suitable: its documented web-app/custom-domain model
does not preserve this repository's Docker Compose, internal PostgreSQL/Redis,
loopback edge, external runtime custody, and exact-origin contract. A
temporary VPS is a last resort only for a separately rebuilt disposable
staging deployment; copying the current database, secrets, browser runtime,
or production configuration to it is prohibited.

Reference material for the access decision: [Tailscale grants](https://tailscale.com/docs/features/access-control/grants),
[Tailscale policy syntax](https://tailscale.com/docs/reference/syntax/policy-file),
[Tailscale Serve TCP forwarding](https://tailscale.com/docs/reference/tailscale-cli/serve),
[PythonAnywhere custom-domain web apps](https://help.pythonanywhere.com/pages/CustomDomains),
and [WireGuard quick start](https://www.wireguard.com/quickstart/).

## Remote access hard gate

- [ ] Security owner selects Tailscale private access for this run and records
      the decision outside Git.
- [ ] The access path is private and identity-restricted; no public DNS route,
      public wildcard listener, or unauthenticated tunnel exists.
- [ ] The path reaches only the staging browser surface. PostgreSQL, Redis,
      Docker, SSH, shell/container, repository, metrics, admin, and management
      surfaces are denied or unroutable to the analyst.
- [ ] The connector/tunnel runs under external custody and has no repository
      copy of its token, private key, or configuration secret.
- [ ] The remote browser still uses exactly
      `https://uwakwe-desktop.taile388cc.ts.net`.
- [ ] The certificate is validated with the approved CA and the
      `uwakwe-desktop.taile388cc.ts.net` SNI/SAN; no `-k`, TLS-ignore, alternate hostname,
      or alternate port is accepted.
- [ ] No redirect, Host header, Origin header, cookie domain, CSRF scope, or
      application base URL changes across the remote path.
- [ ] The analyst device uses the already reviewed browser/provider after
      Tailscale connectivity is established; Tailscale is only the network
      boundary and does not replace Sentinel DNA authentication.
- [ ] A remote smoke test passes without authenticating or mutating state.
      Failure blocks the pilot and does not justify weakening origin checks.

## 1. Preflight and custody

- [ ] Confirm branch and reviewed commit; review `pilot-evidence/gate4/`.
- [ ] Reconcile runtime, lockfile, browser-auth bridge, image, activation
      manifest, TLS, and certified-origin identities with external custody.
- [ ] Confirm populated environment files, TLS keys, browser sessions,
      runtime bundles, backup artifacts, and Tailscale/WireGuard keys are outside
      Git and outside the evidence record.
- [ ] Confirm the staging deployment is disposable and has no production route,
      production volume, production backup, or production credential.
- [ ] Confirm exactly one synthetic tenant and one approved analyst are in
      scope, with bounded expiry and a named operator, reviewer, and rollback
      owner.
- [ ] Obtain specific human security/release approval for this non-production
      pilot through the approved custody process. Do not create an approval in
      Git or in a test fixture.

## 2. Backup and isolated restore evidence

- [ ] Identify staging database owner, backup owner, restore owner, retention,
      recovery contact, schema/migration version, and source deployment digest.
- [ ] Create an immutable staging backup outside the repository without
      overwriting the source or a prior artifact.
- [ ] Record only UTC time, source identity, schema version, artifact size,
      SHA-256, and external custody reference.
- [ ] Validate backup integrity and expected table/schema metadata.
- [ ] Restore into a new isolated disposable target, never over the source.
- [ ] Verify restored tenant separation, provenance columns/linkage, append-only
      audit integrity, health, and readiness behavior.
- [ ] Have the recovery owner attest through the approved external process.
- [ ] Current historical rehearsal says `backup_restore_rehearsal:
      not_executed`; it remains a blocker until these fresh checks pass.

## 3. Deployment and private-boundary validation

- [ ] Start only the approved staging Compose project with external secrets.
- [ ] Confirm app, edge, PostgreSQL, Redis, migration, and evidence-volume
      health.
- [ ] Confirm the edge publication is exactly
      `127.0.0.1:18443->443/tcp`.
- [ ] Confirm the internal network remains isolated and database/Redis have no
      host publication.
- [ ] Confirm Gate 4 readiness returns `READY_FOR_ANALYST_PILOT` with every
      check PASS.
- [ ] Validate `/health` and `/ready` through the certified origin and approved
      CA from the operator host and the remote analyst path.

## 4. Analyst onboarding and authentication evidence

- [ ] Manager signs in only through the approved browser-auth flow.
- [ ] Verify manager role and active session through the application.
- [ ] Verify missing-CSRF denial before any protected write.
- [ ] Provision exactly one synthetic tenant/analyst through the protected
      manager workflow, if authorized for this run.
- [ ] Record only opaque tenant, analyst, authorization, and audit references;
      never record credentials, activation values, cookies, or session IDs.
- [ ] Analyst activates through the approved channel and receives only the
      bounded analyst workspace.
- [ ] Capture direct authentication evidence: actor role, tenant scope,
      authorization expiry, UTC timestamp, and external evidence reference.

## 5. RBAC and tenant-isolation evidence

- [ ] Analyst can perform only the approved synthetic investigation workflow.
- [ ] Analyst cannot access manager/admin escalation, authorization
      management, provisioning, database, shell/container, runtime-management,
      secrets, metrics, or destructive surfaces.
- [ ] Missing-CSRF and every required denial are non-mutating and recorded.
- [ ] Analyst workspace, investigation, result, feedback, and evidence are
      tenant-scoped.
- [ ] A known foreign-tenant synthetic resource returns the documented `403`
      or indistinguishable `404` with no foreign identifier, payload, audit
      content, provenance, or tenant-context leakage.
- [ ] AI output is recorded as advisory-only and remains separate from the
      human analyst conclusion.

## 6. Audit and provenance evidence

- [ ] Audit sink is active before the first authenticated action.
- [ ] Obtain opaque references for manager authentication, CSRF denial,
      provisioning/activation, investigation intake, workspace/result access,
      foreign-tenant denial, privileged denials, feedback, revocation,
      deactivation, and session invalidation.
- [ ] Each event has the required actor, role, tenant, action/denial,
      correlation reference, UTC timestamp, and integrity linkage.
- [ ] Provenance links synthetic input, execution path, result, tenant, and
      human/AI decision separation without sensitive payload serialization.
- [ ] Evidence is append-only or independently hashable, secret-free, and
      stored in approved external custody.

## 7. Revocation test

- [ ] Revoke the analyst authorization with an externally recorded reason.
- [ ] Deactivate the analyst and invalidate all active sessions.
- [ ] Verify subsequent login renewal, workspace reads, investigation reads,
      and feedback/action writes fail closed.
- [ ] Confirm remote access policy is disabled or narrowed after the pilot.
- [ ] Preserve safe audit, provenance, custody, and hash references only.

## 8. Final pilot report

- [ ] Create one new external evidence record conforming to
      `deployment/staging/CONTROLLED_ANALYST_PILOT_EVIDENCE.schema.json`.
- [ ] Set `evidence_class` to
      `authenticated_controlled_analyst_pilot` only for real authenticated
      pilot observations. Rehearsal evidence remains separate.
- [ ] Include source commit, run ID, UTC times, bounded scope, boundary,
      direct gate observations, denial results, audit/provenance references,
      revocation results, evidence hash, and human review decision.
- [ ] Run all validators; every command must exit zero:

  ```powershell
  node deployment/staging/scripts/check_controlled_pilot_readiness.mjs
  node deployment/staging/scripts/validate_authenticated_analyst_access.mjs <evidence-file>
  node deployment/staging/scripts/validate_analyst_rbac.mjs <evidence-file>
  node deployment/staging/scripts/validate_tenant_isolation.mjs <evidence-file>
  node deployment/staging/scripts/validate_audit_trail.mjs <evidence-file>
  node deployment/staging/scripts/validate_session_revocation.mjs <evidence-file>
  node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs <evidence-file>
  ```

- [ ] Review the final report with security/release authority.
- [ ] Record pilot metrics: workflow completion, denial outcomes, audit
      completeness, provenance linkage, revocation latency, and analyst
      feedback, without customer data.
- [ ] Decision is `READY_FOR_CONTROLLED_ANALYST_PILOT_EXECUTION` only after
      all evidence is real, complete, externally held, and human-reviewed.

## Stop and rollback

Stop for public exposure, origin drift, TLS failure, unexpected access,
cross-tenant leakage, missing audit/provenance, credential leakage,
backup/restore failure, unmeasured gates, or provider/runtime drift.

1. Stop analyst activity and preserve the opaque run ID and UTC time.
2. Revoke authorization, deactivate the analyst, invalidate sessions, and
   verify post-revocation denial.
3. Disable the Tailscale grant/Serve listener or the separately approved
   private-access peer.
4. Preserve only safe references and hashes in external custody.
5. Notify the release/security owner; restart only with a new run ID and fresh
   approval.
