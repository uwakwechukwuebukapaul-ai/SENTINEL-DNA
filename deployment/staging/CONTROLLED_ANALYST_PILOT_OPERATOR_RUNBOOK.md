# Controlled Analyst Pilot Operator Runbook

This runbook prepares and executes the final authenticated pilot gates. It is
not an authorization to create an account or issue an endpoint. No account,
credential, activation token, customer data, public DNS record, or public
listener may be created by the preparation procedure.

## 1. Current decision

The pilot remains `BLOCKED_WITH_REASON` until the approved trusted browser RPC
service is available and all authenticated gates produce evidence. The
current preparation run must use `allowProvisioning: false`; it creates no
tenant or analyst account.

## 2. Trusted browser prerequisites

The approved browser capability must provide the orchestration browser object
and its privileged RPC bridge. The expected runtime contract is:

- the approved browser client is available;
- the runtime has a trusted `nodeRepl.rpc` bridge;
- browser setup and execution RPC methods are available;
- the browser has the `browserAuth` capability;
- visible DOM inspection is possible before authentication;
- passwords and tokens are entered only through the secure browser handoff;
- no standalone Playwright, direct HTTP credential client, or alternate
  automation controller is used.

The local Node and browser binaries are not sufficient by themselves. If the
trusted bridge is absent, stop and retain `BLOCKED_WITH_REASON`. Do not start
an alternate service or expose a replacement port.

## 3. Read-only staging precheck

Run these checks from the approved operator environment before browser use:

```powershell
docker version
docker ps --format "{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}"
docker port sentinel-dna-pilot-974e327-edge-1
Resolve-DnsName sentinel-dna-staging
Test-NetConnection 127.0.0.1 -Port 18443
Get-NetTCPConnection -LocalPort 18443 -State Listen
```

The precheck passes only when the edge publication is exactly
`127.0.0.1:18443->443/tcp`, the application/PostgreSQL/Redis services have no
published host ports, and the staging internal network remains internal.
Any `0.0.0.0`, wildcard, LAN, or public listener is an immediate blocker.

Verify the protected Gate 2 image remains available by immutable digest and do
not remove or retag it. Do not print environment files, secrets, or private
key contents during this check.

## 4. Runner safety preflight

Inspect the runner and stop if any of these conditions change:

- manager authentication is not performed through `browserAuth`;
- credentials, cookies, CSRF values, or activation tokens are accepted as
  runner arguments or returned in evidence;
- API requests are not relative same-origin paths;
- provisioning is enabled without a separate written approval and synthetic
  identity review;
- an operator-supplied denial path is missing or is allowed to pass on a
  non-explicit response;
- audit/provenance checks only observe HTTP 200 without a verifiable reference;
- evidence can overwrite an existing run;
- the run accepts a public or non-loopback origin.

The current source review finds the first, third, fifth, and evidence
exclusive-create controls present. It also finds conditional limitations in
synthetic identity enforcement, hostname-to-loopback enforcement, secret-field
coverage, and audit/provenance response verification. Treat those limitations
as `NEEDS_REVIEW`; they are not evidence of a passed pilot.

## 5. Authenticated execution after bridge availability

Only after the prerequisites pass, run the module inside the trusted browser
session. Keep provisioning disabled for the prepared run:

```js
var pilotRunner = await import("C:/Users/HP/Documents/sentinel-dna-postmerge-ssh/deployment/staging/scripts/controlled_analyst_pilot_runner.mjs");
var result = await pilotRunner.runControlledAnalystPilot({
  browser,
  origin: "https://sentinel-dna-staging:18443",
  runId: "PILOT-RUN-<operator-assigned>",
  allowProvisioning: false,
  analyst: {
    tab: analystTab,
    runId: "PILOT-RUN-<operator-assigned>",
    expectedTenantId: "<approved-synthetic-tenant-id>",
    foreignTenantResourcePath: "<known-foreign-tenant-synthetic-resource>",
    auditPath: "<known-tenant-scoped-audit-path>",
    provenancePath: "<known-tenant-scoped-provenance-path>",
    aiVerificationPath: "<known-investigation-result-path>",
    denialPaths: {
      deny_database: ["<known-database-control-path>"],
      deny_shell_container: ["<known-shell-or-container-control-path>"],
      deny_destructive: ["<known-destructive-action-path>"]
    }
  }
});
result.status
```

The analyst tab, tenant ID, foreign resource, audit path, provenance path, AI
verification path, and denial paths must be supplied from the reviewed staging
contract. Placeholder values are not executable. `analystTab` must represent
the one approved synthetic analyst session; do not create a second account.

If provisioning is later authorized, it is a separate controlled operation:
the manager must use the secure handoff, the identity must be synthetic, the
activation token must be transferred out-of-band, and the token must never
enter logs, source control, or evidence. This runbook does not authorize that
operation.

## 6. PASS criteria

The result can be considered for human release approval only if every required
gate is `PASS` and none is `FAIL`, `NOT_MEASURED`, `NOT_PERFORMED`, `UNKNOWN`,
or `NEEDS_REVIEW`:

- manager session and role are confirmed;
- CSRF is required for writes and missing CSRF is denied without state change;
- the analyst role and exact synthetic tenant scope are server-derived;
- cross-tenant, admin, production, database, shell/container, and destructive
  actions are explicitly denied;
- the synthetic investigation workflow succeeds through the canonical path;
- audit and provenance references prove the action and tenant scope;
- AI output is advisory-only and a human decision is required;
- secure cookie/session behavior is confirmed;
- evidence is secret-free, append-only, uniquely named, timestamped UTC, and
  hash-verified;
- revocation, session invalidation, and fail-closed post-revocation behavior
  are verified by the operator;
- the human release authority records the final decision.

No analyst URL is issued by the runner. A private endpoint may be issued only
after the human decision is recorded and the endpoint remains private.

## 7. Evidence workflow

Write only non-secret results to the approved evidence directory:

`C:/ProgramData/Sentinel-DNA/release/evidence/`

Use a new timestamped or unique run identifier. Never overwrite prior
evidence. Record timestamps in UTC, immutable runtime identifiers, image and
configuration digests, certificate fingerprint, gate results, tenant-scoped
audit/provenance references, and the access-boundary results. Do not record
passwords, cookies, CSRF tokens, activation tokens, private keys, database
dumps, or customer data.

If a result is not measurable, write `NOT_MEASURED` and keep the decision
blocked. Do not infer a pass from a healthy endpoint or an HTTP status alone.

## 8. Rollback and revocation

On failure, suspected exposure, or pilot completion:

1. Revoke the pilot authorization with a reason.
2. Deactivate the synthetic analyst and invalidate active sessions.
3. Disable or restrict the private edge if compromise is suspected.
4. Verify login, workspace, investigation, and feedback writes fail closed.
5. Preserve non-secret audit, provenance, monitoring, and evidence records.
6. Restore only into a separate disposable staging target if recovery is
   required; never restore over production.

## 9. Required handoff

The operator hands off the evidence paths, hashes, blockers, and revocation
result to the human release authority. The final decision is either
`READY_FOR_CONTROLLED_ANALYST_PILOT` or `BLOCKED_WITH_REASON`; no intermediate
status authorizes access.
