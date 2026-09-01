# Sentinel DNA Controlled Analyst Pilot
# External Operator Activation Package

**Purpose:** production-safe onboarding for one bounded SOC analyst pilot.
**Environment:** staging only.
**Current repository decision:** `BLOCKED_WITH_REASON` until the external
reviewed runtime, activation manifest, staging deployment evidence, and human
approval are present.
**Authorization:** this package does not authorize account creation,
credential issuance, customer access, endpoint publication, or pilot
execution.

This package is for the approved operator/security team. It supplements the
[Trusted Browser Provider Configuration](./TRUSTED_BROWSER_PROVIDER_CONFIGURATION.md),
[Activation Checklist](./CONTROLLED_ANALYST_PILOT_ACTIVATION_CHECKLIST.md), and
[Operator Runbook](./CONTROLLED_ANALYST_PILOT_OPERATOR_RUNBOOK.md). If any
requirement is missing, stale, contradictory, or unverifiable, stop and retain
`BLOCKED_WITH_REASON`.

The authoritative validation scripts are already present in this repository;
this package does not create a second execution path. They are read-only
operator checks, and none of them authorizes a pilot by itself:

- `configure_trusted_browser_provider.ps1 -DryRun` validates non-secret
  configuration and referenced files without printing values;
- `verify_trusted_browser_provider.mjs` validates the external runtime/provider
  contract and `browserAuth` without authentication;
- `check_controlled_pilot_readiness.mjs` validates image identity, manifest,
  staging environment, evidence custody, certified-origin reachability, and
  deployment security assertions;
- `generate_trusted_browser_readiness_report.mjs` emits the machine-readable
  readiness report;
- `check_controlled_pilot_activation.ps1` is the authoritative operator gate;
- `validate_manual_analyst_pilot_evidence.mjs` validates the completed
  tenant-isolation, audit/provenance, analyst-scope, revocation, and human
  approval evidence after the controlled run.

No new provider, test fallback, credential path, or bypass is part of this
validation package.

## 1. Architecture and activation boundary

The production chain is fixed:

```text
controlled analyst pilot runner
  -> trusted browser execution adapter
  -> Sentinel DNA trusted browser facade
  -> checked-in provider boundary
  -> external reviewed Playwright/RPC runtime
  -> operator-approved browserAuth capability
```

The repository facade and provider boundary do not install Playwright, launch
an alternate browser, connect to CDP, perform direct HTTP authentication, or
store credentials, cookies, tokens, or browser sessions. The external runtime
owns the reviewed browser/RPC lifecycle. Sentinel DNA accepts only the
certified staging origin and the `codex-app` environment.

Provider verification is read-only: it imports the configured modules, checks
the runtime/browser/tab contract and discovers `browserAuth`, then closes its
temporary probe tab where supported. It does not authenticate or call
`browserAuth.request()`.

## 2. Required external runtime installation

The operator must obtain the external reviewed Playwright/RPC runtime from the
approved internal distribution or vendor custody system. Do not obtain it by
adding a dependency to this repository or by installing a standalone
Playwright browser as a substitute.

Before registration, record in the security change or approval system:

- runtime package/module identity and version;
- supplier/release provenance and review reference;
- SHA-256 digest of the exact runtime artifact/module;
- reviewer, review date, and approved staging image/runtime scope;
- confirmation that the runtime uses the trusted RPC bridge and does not
  expose CDP, debugging ports, public listeners, or alternate authentication;
- approved teardown, session invalidation, and incident contacts.

Install the reviewed runtime only on the approved private operator/trusted
browser host. Keep signing keys, credentials, cookies, tokens, session state,
and any runtime secrets outside the repository and outside readiness reports.

The installed runtime module must export exactly the reviewed entrypoint:

```js
export async function setupBrowserRuntime({ environment }) {
  return {
    browsers: {
      getForUrl(origin) {
        // External reviewed implementation; certified origin only.
      },
    },
  };
}
```

The module must accept only `environment: "codex-app"`. Its returned runtime
must provide `browsers.getForUrl(origin)`. The selected browser must provide
`tabs.new()`. Each tab must provide `goto()`,
`playwright.locator()`, `playwright.evaluate()`,
`dom_cua.get_visible_dom()`, and `capabilities.get("browserAuth")`.

Do not configure a test fixture, local stub, browser endpoint, CDP URL,
debugging port, HTTP client, or arbitrary module as the external runtime.

## 3. Required operator environment

Set these non-secret values only in the approved operator/runtime environment.
Do not commit them or print their values in logs.

```powershell
$repoRoot = "C:\path\to\sentinel-dna-postmerge-ssh"
$env:SENTINEL_DNA_TRUSTED_BROWSER_CLIENT = "$repoRoot\deployment\staging\scripts\trusted_browser_service\browser-client.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT = "$repoRoot\deployment\staging\scripts\trusted_browser_service\providers\playwright-runtime-provider.mjs"
$env:SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = "C:\approved\browser\playwright-runtime.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST = "C:\approved\browser\trusted-browser-activation-manifest.json"
$env:SENTINEL_DNA_IMAGE_DIGEST = "sha256:<64-hex-deployed-staging-image-digest>"
$env:SENTINEL_DNA_ENV = "staging"
$env:SENTINEL_DNA_PILOT_ACCESS_REQUIRED = "1"
$env:SENTINEL_DNA_SECURE_COOKIES = "1"
$env:FLASK_DEBUG = "0"
$env:SENTINEL_DNA_TENANT_ISOLATION_ENABLED = "1"
$env:SENTINEL_DNA_AUDIT_LOGGING_ENABLED = "1"
```

The digest and boolean assertions are readiness inputs, not secrets. The
tenant-isolation and audit assertions must be true in the deployed staging
application; setting them only in the operator shell is insufficient.

The configuration helper validates required values and referenced files
without printing values:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
```

Any missing or invalid input is a blocker. Never resolve it by changing the
certified origin, accepting a test fixture, disabling a check, or passing
credentials through an environment variable.

## 4. Activation manifest schema

Create the manifest through the approved custody/approval workflow outside
Git. It is non-secret and must not contain paths, credentials, cookies,
tokens, browser session values, or signing keys.

Required format:

```json
{
  "schema_version": "1.0",
  "provider_identity": "reviewed-provider:provider-2026-09",
  "runtime_module_identity": "reviewed-runtime:runtime-2026-09",
  "approved_image_runtime_digest": "sha256:<64-hex-digest>",
  "staging_origin": "https://sentinel-dna-staging:18443",
  "activation_timestamp": "2026-09-01T12:00:00Z",
  "operator_approval_reference": "APPROVAL-2026-09-001",
  "integrity": {
    "algorithm": "sha256",
    "manifest_hash": "<64-hex-canonical-payload-hash>"
  }
}
```

The optional detached signature metadata is allowed only when supplied and
verified by the external custody system:

```json
{
  "signature": {
    "scheme": "detached-external",
    "key_reference": "approved-key-reference",
    "signature_reference": "approved-signature-reference"
  }
}
```

The checked-in validator requires:

- schema version `1.0`;
- safe provider/runtime identities and approval reference;
- an image digest matching `sha256:` plus 64 hexadecimal characters;
- the exact certified origin;
- a UTC activation timestamp;
- `integrity.algorithm` equal to `sha256`;
- a 64-hex `integrity.manifest_hash` matching the canonical payload.

## 5. SHA-256 digest reconciliation

Reconcile two separate identities before activation:

1. Obtain the immutable digest of the actually deployed staging image from
   the approved deployment system. Do not rely on a mutable tag.
2. Set `SENTINEL_DNA_IMAGE_DIGEST` to that exact `sha256:<64-hex>` value.
3. Put the same value in
   `approved_image_runtime_digest` in the externally held manifest.
4. Compute `integrity.manifest_hash` over the canonical manifest payload with
   the complete `integrity` object excluded. Canonicalization recursively
   sorts object keys; array order is preserved; the result is UTF-8 JSON with
   no added whitespace or newline.
5. Place the resulting lowercase SHA-256 hex digest in
   `integrity.manifest_hash`.
6. If detached signing is required, sign/approve the manifest through the
   external custody system after hashing. Keep signing material out of the
   repository and operator reports.
7. Run readiness. A manifest/image mismatch must produce a blocked result.

The repository validator performs the manifest hash check and compares the
manifest image digest to `SENTINEL_DNA_IMAGE_DIGEST` when the configured image
digest is valid. Do not hand-edit a report to make the identities agree.

## 6. Trusted browser provider onboarding

Register the checked-in modules in this order:

1. `trusted_browser_service/browser-client.mjs` is the facade selected by the
   execution adapter.
2. `trusted_browser_service/providers/playwright-runtime-provider.mjs` is the
   provider boundary configured as the upstream client.
3. `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME` points to the external reviewed
   runtime module.

The provider boundary forwards only `{ environment: "codex-app" }` and exposes
only certified-origin selection. The facade performs the final browser/tab,
Playwright, visible-DOM, origin, redaction, and `browserAuth` checks.

Run verification before any pilot use:

```powershell
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
```

Every check must pass. Safe failures include
`TB_PROVIDER_NOT_CONFIGURED`, `TB_PROVIDER_MODULE_MISSING`,
`TB_PROVIDER_EXPORT_INVALID`, `TB_RUNTIME_UNAVAILABLE`,
`TB_BROWSER_SELECTION_FAILED`, `TB_BROWSER_CONTRACT_FAILED`, and
`TB_AUTH_CAPABILITY_MISSING`. Do not inspect or print upstream exceptions to
diagnose them; use the corresponding operator/runtime review channel.

## 7. Tenant-isolation verification

The deployment owner must provide evidence from the actual staging application,
not merely an environment-variable assertion. Use one approved synthetic
tenant and one separately controlled foreign-tenant resource.

Verify and retain non-secret evidence that:

- the analyst identity and tenant are server-derived and match the approved
  scope;
- the analyst can access only the approved tenant's investigation/workspace;
- a foreign-tenant resource is denied or safely indistinguishable from not
  found;
- administrative, production, database, shell/container, destructive, and
  cross-tenant actions are denied;
- tenant IDs and access decisions are recorded without credential material;
- post-revocation access fails closed;
- the staging application is not connected to production data or control
  planes.

The evidence must include run ID, UTC timestamps, immutable image/runtime
identities, check results, and tenant-scoped references. It must not include
customer data, passwords, cookies, CSRF values, activation tokens, or session
material.

## 8. Audit evidence collection

Before approval, verify that audit logging is enabled in the staging
deployment and that the audit sink is available to the approved reviewers.
Collect only non-secret references:

- audit event IDs or immutable references;
- UTC event timestamps;
- approved run ID and tenant scope;
- actor role and decision type, excluding credentials;
- image/runtime/manifest identities and hashes;
- evidence file hashes and custody location;
- denial, revocation, teardown, and post-revocation verification results;
- operator and human approval references.

Do not copy request headers, authorization values, cookies, tokens, password
fields, private keys, database dumps, or raw customer records into evidence.
Audit evidence must be access-controlled, append-only by procedure, retained
under the approved SOC/customer evidence policy, and reviewable without
granting additional pilot access.

Generate the safe readiness report and preserve it as an activation artifact:

```powershell
node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
node .\deployment\staging\scripts\generate_trusted_browser_activation_troubleshooting_report.mjs
```

The troubleshooting command is for blocked remediation only. It does not
authorize execution.

## 9. Security approval checklist

The human security/release authority must review direct evidence for every
item:

- [ ] External runtime provenance, review record, and immutable digest are
      recorded.
- [ ] Trusted RPC bridge is available; no CDP, debugging port, public listener,
      alternate RPC, or standalone Playwright substitute is configured.
- [ ] Checked-in facade and provider boundary are registered at the expected
      module identities.
- [ ] Provider exports `setupBrowserRuntime` and accepts only `codex-app`.
- [ ] Runtime/browser/tab contract passes, including visible DOM and
      Playwright surfaces.
- [ ] External `browserAuth` capability is present and credential entry stays
      outside Sentinel DNA.
- [ ] Certified origin is exactly
      `https://sentinel-dna-staging:18443` and TLS/private-edge checks pass.
- [ ] Manifest schema, provider identity, runtime identity, approval
      reference, timestamp, and SHA-256 hash pass validation.
- [ ] Manifest digest exactly matches the deployed immutable image digest.
- [ ] Staging environment is confirmed; secure cookies are enabled and debug
      is disabled.
- [ ] Pilot access gate is enabled and no public exposure exists.
- [ ] Tenant isolation and cross-tenant denial have been verified.
- [ ] Audit logging and provenance are enabled, tenant-scoped, and reviewable.
- [ ] Evidence directory is writable by the approved process and controlled by
      append-only custody procedures.
- [ ] Node and Python staging security tests pass for the release candidate.
- [ ] Customer scope, synthetic-data boundary, access list, and stop
      conditions are approved.
- [ ] Rollback and analyst revocation procedures are tested and owned.
- [ ] Human authority has recorded approval after reviewing the complete
      readiness artifact.

Only a final `READY_FOR_ANALYST_PILOT` result plus completed human approval may
advance the workflow. Any unchecked item is `BLOCKED_WITH_REASON`.

## 10. Pilot activation commands

Run from the repository root on the approved operator host:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

Proceed only when the activation result is:

```json
{"status":"READY_FOR_ANALYST_PILOT","codes":[]}
```

Then run the normal activation command to create the non-secret readiness
artifact:

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1
```

The activation gate does not authenticate, create an account, provision a
tenant, or authorize an analyst session. The runner remains subject to
browserAuth, tenant, denial, audit/provenance, evidence, revocation, and human
approval gates.

## 11. Machine-readable readiness report

The report emitted by
`generate_trusted_browser_readiness_report.mjs` is defined by
[`CONTROLLED_ANALYST_PILOT_READINESS_REPORT.schema.json`](./CONTROLLED_ANALYST_PILOT_READINESS_REPORT.schema.json).
It contains statuses and safe reasons only; it must not contain provider paths,
environment values, credentials, cookies, tokens, session data, customer data,
or stack traces.

The report must contain these checks:

| Check | Evidence source | Failure behavior |
| --- | --- | --- |
| `provider_configured` | Operator configuration preflight | `BLOCKED_WITH_REASON` with `TB_PROVIDER_NOT_CONFIGURED` |
| `runtime_reachable` | Provider verification | Blocked with the safe `TB_*` runtime category |
| `browser_contract_valid` | Provider verification and facade contract checks | `TB_BROWSER_CONTRACT_FAILED` |
| `origin_reachable` | Certified HTTPS staging-origin check | `TB_ORIGIN_UNREACHABLE` |
| `browser_auth_available` | External capability discovery | `TB_AUTH_CAPABILITY_MISSING` |
| `evidence_directory_writable` | Readiness filesystem check | `TB_EVIDENCE_DIRECTORY_UNAVAILABLE` |
| `audit_prerequisites_available` | Security assertions for cookies, debug, pilot gate, tenant isolation, and audit logging | `TB_SECURITY_CONTROL_MISSING` |
| `activation_manifest_valid` | Manifest schema/hash/origin/image reconciliation | `TB_PROVIDER_MANIFEST_MISSING` or `TB_PROVIDER_MANIFEST_INVALID` |

An example report shape is:

```json
{
  "schema_version": "1.0",
  "generated_at_utc": "2026-09-01T12:00:00.000Z",
  "status": "BLOCKED_WITH_REASON",
  "manifest_status": "BLOCKED",
  "provider_status": "BLOCKED",
  "image_digest_status": "BLOCKED",
  "origin_status": "BLOCKED",
  "tenant_isolation_status": "BLOCKED",
  "audit_status": "BLOCKED",
  "final_readiness_decision": "BLOCKED_WITH_REASON",
  "checks": [
    {
      "name": "provider_configured",
      "status": "BLOCKED",
      "reason": "TB_PROVIDER_NOT_CONFIGURED"
    }
  ]
}
```

`READY_FOR_ANALYST_PILOT` is valid only when every required check is `PASS`.
The report is a readiness artifact, not a substitute for the human approval
workflow or the post-run evidence validator.

## 12. Tenant, audit, and analyst approval validation

The pre-run readiness report confirms deployment prerequisites. It cannot prove
that an analyst session actually remained within its tenant or that each
sensitive action was audited. Those facts must be demonstrated by the
controlled run and validated with:

```powershell
node .\deployment\staging\scripts\validate_manual_analyst_pilot_evidence.mjs `
  C:\ProgramData\Sentinel-DNA\release\evidence\<manual-evidence-file>.json
```

The evidence validator must report `VERIFIED` before customer documentation
or pilot release. The evidence must prove:

- one approved synthetic analyst and one approved synthetic tenant;
- server-derived analyst role and tenant scope;
- foreign-tenant and privileged-action denial;
- tenant-scoped audit, action, and provenance references;
- secret-free, customer-data-free evidence;
- authorization revocation, analyst deactivation, session invalidation, and
  post-revocation fail-closed behavior;
- human release approval and no analyst URL issued before approval.

The analyst access approval workflow is external to browser automation:

1. Security/release authority approves the bounded analyst, tenant, dates,
   scenarios, and revocation owner.
2. The operator records the non-secret approval reference in the approved
   manifest/custody record.
3. The readiness gate passes before any analyst session is used.
4. The human authority reviews completed evidence and explicitly approves or
   rejects release.
5. Any missing approval, stale reference, or unverified evidence remains
   `BLOCKED_WITH_REASON`.

The analyst URL remains unissued until the human decision is recorded.

## 13. Pilot rollback procedure

On any security anomaly, failed control, unexpected access, evidence issue,
runtime fault, or pilot completion:

1. Stop pilot activity and record the non-secret run ID and UTC time.
2. Revoke the pilot authorization through the approved identity/control-plane
   procedure.
3. Invalidate active analyst sessions and deactivate the synthetic analyst
   scope as approved; do not copy or handle credentials in this procedure.
4. Disable or restrict the private staging edge if compromise or unintended
   exposure is suspected.
5. Verify login, workspace, investigation, feedback, cross-tenant, and
   privileged writes fail closed as applicable.
6. Stop or tear down the external browser runtime using its reviewed lifecycle
   procedure. Do not kill or reconnect through an unreviewed endpoint.
7. Preserve non-secret audit, provenance, readiness, evidence hashes, and
   incident references under custody. Do not preserve browser sessions or
   credential material.
8. Notify the security incident owner and human release authority.
9. Do not reactivate until a new readiness report, security review, and human
   approval are complete.

Rollback is a block, not a reason to relax origin, capability, tenant, audit,
or evidence validation.

## 14. Analyst access revocation procedure

Revocation must be performed by the authorized identity/control-plane owner:

1. Record the analyst, tenant scope, approval reference, run ID, revocation
   reason, and UTC timestamp in the approved control record.
2. Revoke the pilot authorization and invalidate active sessions through the
   approved service control; do not request, record, or transport credentials.
3. Remove the analyst from the pilot allowlist or disable the synthetic pilot
   identity according to the approved staging procedure.
4. Verify that the former analyst cannot access the workspace, investigation,
   feedback, or tenant resources after revocation.
5. Verify cross-tenant and privileged actions remain denied.
6. Confirm the revocation and post-revocation denial events are present in the
   tenant-scoped audit trail.
7. Close the external runtime/browser session through its reviewed teardown
   path and confirm no browser session is retained in repository or evidence
   storage.
8. Archive the revocation result and evidence hash under approved custody.

If revocation cannot be verified, the pilot remains blocked and the incident
owner must treat the condition as a security event.

## 15. Final activation decision

This package does not change the current repository decision. The controlled
analyst pilot may proceed only when:

- provider verification passes;
- the activation manifest is valid and digest-reconciled;
- the certified origin is reachable over approved private TLS;
- tenant isolation and audit evidence are verified;
- evidence custody is ready;
- all security checklist items are complete; and
- the human release authority records approval.

Otherwise the only permitted result is `BLOCKED_WITH_REASON` with safe
diagnostic codes. No mocks, test fallbacks, credentials, direct-login paths,
CDP paths, or validation bypasses are permitted.
