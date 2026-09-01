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

Use [`CONTROLLED_ANALYST_PILOT_ACTIVATION_CHECKLIST.md`](./CONTROLLED_ANALYST_PILOT_ACTIVATION_CHECKLIST.md)
as the final operator sign-off checklist. It does not replace the human
approval gate or the evidence validator.

## 2. Trusted browser prerequisites

The approved browser capability must provide the orchestration browser object
and its privileged RPC bridge. Configure the checked-in trusted-browser client
as the adapter entrypoint and configure the checked-in provider boundary with
the separately reviewed Playwright runtime module:

```powershell
$env:SENTINEL_DNA_TRUSTED_BROWSER_CLIENT = "C:\Users\HP\Documents\sentinel-dna-postmerge-ssh\deployment\staging\scripts\trusted_browser_service\browser-client.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT = "C:\Users\HP\Documents\sentinel-dna-postmerge-ssh\deployment\staging\scripts\trusted_browser_service\providers\playwright-runtime-provider.mjs"
$env:SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = "C:\approved\browser\playwright-runtime.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST = "C:\approved\browser\trusted-browser-activation-manifest.json"
```

The second path is the checked-in provider boundary. The third path is a local
module path, not a browser endpoint or a credential. It must point to the
separately reviewed operator runtime that owns the trusted Playwright/RPC
transport. Do not replace it with a local `playwright` install, CDP endpoint,
browser-debugging port, or standalone HTTP client. The checked-in provider and
client do not launch a browser or make network calls themselves.

The checked-in
`deployment/staging/scripts/trusted_browser_service/runtime-provider.mjs` is
the production-safe provider interface. The operator module must export only
the reviewed runtime entrypoint:

```js
export async function setupBrowserRuntime({ environment }) {
  // The external reviewed runtime owns the trusted Playwright/RPC transport.
  return { browsers: { getForUrl(origin) { /* provider implementation */ } } };
}
```

The checked-in provider loads the module named by
`SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME`, invokes it with
`{ environment: "codex-app" }`, and accepts the runtime only when it provides
`browsers.getForUrl(origin)`. The selected
browser must provide `tabs.new()`, tab `goto()`, Playwright `locator()` and
`evaluate()`, visible DOM inspection, capability discovery, and the external
`browserAuth` capability. No provider options, credentials, cookies, tokens,
or browser session values are forwarded through this interface.

The test-only contract stub at
`tests/staging/fixtures/trusted-playwright-adapter-stub.mjs` is suitable only
for local staging contract tests. It is not a runtime provider and must never
be configured for an authenticated pilot.

If setup fails, the diagnostic code identifies the fail-closed layer without
printing paths, upstream exception text, or secrets. Common codes are
`TB_PROVIDER_NOT_CONFIGURED`, `TB_PROVIDER_MODULE_MISSING`,
`TB_PROVIDER_EXPORT_INVALID`, `TB_RUNTIME_UNAVAILABLE`,
`TB_BROWSER_SELECTION_FAILED`, `TB_BROWSER_CONTRACT_FAILED`, and
`TB_AUTH_CAPABILITY_MISSING`. A missing or untrusted provider remains a pilot
blocker.

The expected runtime contract is:

- the approved browser client is available;
- the runtime has a trusted `nodeRepl.rpc` bridge;
- browser setup and execution RPC methods are available;
- the browser has the `browserAuth` capability;
- visible DOM inspection is possible before authentication;
- passwords and tokens are entered only through the secure browser handoff;
- no standalone Playwright, direct HTTP credential client, or alternate
  automation controller is used.

The checked-in client selects exactly
`https://sentinel-dna-staging:18443`. Its `tabs.new()` façade exposes only the
runner's Playwright locator/evaluation surface, visible DOM inspection, and
the external `browserAuth` capability. Navigation outside the certified
origin is rejected. Evaluation and DOM results are redacted for
secret-shaped fields, and `browserAuth.request()` returns only its protocol
status; passwords, cookies, tokens, and richer capability results do not cross
the runner boundary.

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

## 5. Operator execution workflow

### Operational activation sequence

The operator must complete this sequence in order. Every command is
fail-closed; a blocked result stops the sequence and must not be worked around
with a test fixture or alternate browser service.

1. Configure the reviewed runtime and non-secret readiness assertions using
   the exact configuration in `TRUSTED_BROWSER_PROVIDER_CONFIGURATION.md`.
2. Run provider verification.
3. Run the single controlled-pilot activation gate.
4. Execute the pilot.
5. Validate the evidence record.
6. Archive the evidence manifest under the approved append-only custody
   procedure.

### Step 0: Configure and verify trusted browser provider

After setting the provider variables above, run the safe configuration check.
Use `-DryRun` while reviewing the operator environment; the command never
prints variable values or changes the environment:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
```

Then run the read-only verification command from the approved
operator/trusted-browser runtime environment:

```powershell
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
```

Continue only when the command reports `"status": "PASS"` and every check is
`PASS`. It does not authenticate, call `browserAuth.request()`, navigate,
evaluate page code, or write evidence. Any `TB_*` failure leaves the pilot
blocked; do not substitute the test fixture or start another browser service.

The activation manifest must be present, hash-valid, and reference the
certified staging origin and reviewed image/runtime identity.

### Step 0.5: Run controlled-pilot activation gate

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1
```

Continue only when the command reports `READY_FOR_ANALYST_PILOT`. It invokes
the machine-readable provider report and readiness checker, and confirms the
immutable image identity, activation-manifest binding, staging environment,
provider verification, writable evidence custody directory, validation
scripts, certified-origin reachability, secure cookies, disabled debug, tenant
isolation, and audit logging. Normal mode writes only the non-secret readiness artifact
`pilot-evidence/controlled-pilot-readiness-report-<timestamp>.json`; it does
not create pilot evidence or authenticate.

Use `-DryRun` when validating configuration without creating the readiness
artifact.

If activation is blocked, generate the safe troubleshooting report for the
operator or security reviewer:

```powershell
node .\deployment\staging\scripts\generate_trusted_browser_activation_troubleshooting_report.mjs
```

For automation, request JSON from the activation gate:

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

### Step 1: Run controlled analyst pilot

Only after Step 0 passes, execute the controlled pilot wrapper described below
with a new operator-assigned non-secret run identifier. Keep provisioning
disabled.

### Step 2: Validate evidence

Validate the separately captured manual evidence record with the unchanged
validator. The validator must report `VERIFIED`; otherwise retain the blocked
decision:

```powershell
node .\deployment\staging\scripts\validate_manual_analyst_pilot_evidence.mjs `
  C:\ProgramData\Sentinel-DNA\release\evidence\<manual-evidence-file>.json
```

### Step 3: Review human approval gate

The human release authority reviews all gate results, evidence hashes,
tenant-scoped audit/provenance references, revocation results, and remaining
`NEEDS_REVIEW` or `NOT_MEASURED` items. Only that authority may record
`READY_FOR_CONTROLLED_ANALYST_PILOT`; otherwise record
`BLOCKED_WITH_REASON`.

## 6. Authenticated execution after bridge availability

Only after the prerequisites pass, run the standalone wrapper from the trusted
browser service's JavaScript runtime. The wrapper uses
`trusted_browser_execution_adapter.mjs` to obtain the browser through the
trusted RPC bridge and performs a capability preflight before calling the
runner. It never starts a local browser or accepts credential material.

From the trusted browser service runtime, execute the wrapper with a new
operator-assigned run identifier:

```js
var pilot = await import("C:/Users/HP/Documents/sentinel-dna-postmerge-ssh/deployment/staging/scripts/run_controlled_analyst_pilot.mjs");
var result = await pilot.executeControlledAnalystPilot({
  runId: "PILOT-RUN-<operator-assigned-unique-id>"
});
result.status
```

For a normal process invocation, the same wrapper accepts only the
non-secret run identifier as its first argument:

```powershell
node .\deployment\staging\scripts\run_controlled_analyst_pilot.mjs PILOT-RUN-<operator-assigned-unique-id>
```

That process must still be hosted by the approved browser service; a regular
Node process without its trusted RPC bridge fails closed. Keep provisioning
disabled for the prepared run. The wrapper's manager preflight does not create
an analyst account and does not claim analyst-gate or revocation evidence.

When the one approved synthetic analyst session and the reviewed, non-secret
endpoint paths are available, the same browser object may be passed to the
runner from the trusted browser service runtime:

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

The adapter contract is intentionally narrow: it selects only
`https://sentinel-dna-staging:18443`, requires visible DOM inspection,
Playwright page evaluation/locators, and the tab-level `browserAuth` capability,
then closes its temporary probe tab. The runner still performs the
`browserAuth` handoff, tenant isolation, audit, provenance, denial, and
AI-advisory checks; the adapter cannot mark any gate as passed.

The analyst tab, tenant ID, foreign resource, audit path, provenance path, AI
verification path, and denial paths must be supplied from the reviewed staging
contract. Placeholder values are not executable. `analystTab` must represent
the one approved synthetic analyst session; do not create a second account.

If provisioning is later authorized, it is a separate controlled operation:
the manager must use the secure handoff, the identity must be synthetic, the
activation token must be transferred out-of-band, and the token must never
enter logs, source control, or evidence. This runbook does not authorize that
operation.

## 7. PASS criteria

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

## 8. Evidence workflow

Write only non-secret results to the approved evidence directory:

`C:/ProgramData/Sentinel-DNA/release/evidence/`

Use a new timestamped or unique run identifier. Never overwrite prior
evidence. Record timestamps in UTC, immutable runtime identifiers, image and
configuration digests, certificate fingerprint, gate results, tenant-scoped
audit/provenance references, and the access-boundary results. Do not record
passwords, cookies, CSRF tokens, activation tokens, private keys, database
dumps, or customer data.

The wrapper writes its append-only preparation record as:

`C:/ProgramData/Sentinel-DNA/release/evidence/controlled-analyst-pilot-<run-id>.json`

Validate the operator-captured manual evidence record with the unchanged
validator:

```powershell
node .\deployment\staging\scripts\validate_manual_analyst_pilot_evidence.mjs `
  C:\ProgramData\Sentinel-DNA\release\evidence\<manual-evidence-file>.json
```

The wrapper's preparation record is intentionally `BLOCKED_WITH_REASON` when
analyst gates or revocation have not been measured and does not satisfy the
manual validator's `VERIFIED` release-evidence schema. Do not convert or fill
those gates in by hand; complete the authenticated operator procedure and
validate that separately captured record.

If a result is not measurable, write `NOT_MEASURED` and keep the decision
blocked. Do not infer a pass from a healthy endpoint or an HTTP status alone.

## 9. Rollback and revocation

On failure, suspected exposure, or pilot completion:

1. Revoke the pilot authorization with a reason.
2. Deactivate the synthetic analyst and invalidate active sessions.
3. Disable or restrict the private edge if compromise is suspected.
4. Verify login, workspace, investigation, and feedback writes fail closed.
5. Preserve non-secret audit, provenance, monitoring, and evidence records.
6. Restore only into a separate disposable staging target if recovery is
   required; never restore over production.

## 10. Required handoff

The operator hands off the evidence paths, hashes, blockers, and revocation
result to the human release authority. The final decision is either
`READY_FOR_CONTROLLED_ANALYST_PILOT` or `BLOCKED_WITH_REASON`; no intermediate
status authorizes access.
