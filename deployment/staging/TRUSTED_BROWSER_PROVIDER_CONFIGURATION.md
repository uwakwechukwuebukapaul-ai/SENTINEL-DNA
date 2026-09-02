# Trusted Browser Provider Configuration

This document defines the operator contract for the Sentinel DNA controlled
analyst pilot trusted-browser chain. It does not authorize account creation,
credential issuance, or pilot release. The pilot remains blocked until the
provider and trusted RPC bridge pass verification and the human release gate
is satisfied.

## Provider responsibilities

The operator-supplied reviewed runtime provider owns the approved
Playwright/RPC transport. It is responsible for:

- starting or connecting to the approved browser runtime through its reviewed
  platform configuration;
- returning the orchestration runtime contract;
- enforcing the trusted service lifecycle and RPC availability;
- exposing the external `browserAuth` capability supplied by the trusted
  browser service;
- closing or releasing browser resources according to the approved runtime
  lifecycle.

The provider must not accept passwords, tokens, cookies, session values, or
credential-bearing options from Sentinel DNA. It must not write secrets to
logs, files, evidence, or repository state.

## Required exports and runtime contract

The configured reviewed runtime module must export:

```js
export async function setupBrowserRuntime({ environment }) {
  // The reviewed operator runtime owns the Playwright/RPC transport.
  return {
    browsers: {
      getForUrl(origin) {
        // Return the approved browser for the certified origin only.
      },
    },
  };
}
```

The only accepted environment is `codex-app`. The resulting browser must
provide `tabs.new()`. Each returned tab must provide:

- `goto(url)` restricted to the certified staging origin;
- `playwright.locator()` and `playwright.evaluate()`;
- `dom_cua.get_visible_dom()`;
- `capabilities.get("browserAuth")` returning the external capability.

### Browser authentication bridge contract

The operator environment must set the non-secret module path
`SENTINEL_DNA_BROWSER_AUTH_BRIDGE` to a separately reviewed local module. The
module must export a callable `requestBrowserAuth` function with this shape:

```js
export async function requestBrowserAuth({ page, request, environment }) {
  // Use the approved browser UI to obtain credentials; never accept them in
  // this request or return them to Sentinel DNA.
  return { status: "submitted" };
}
```

The adapter supplies only `environment: "codex-app"`, the certified origin,
visible login-field descriptors, and selector strings. A valid bridge must
perform credential entry through the browser-mediated handoff and return only
a non-secret string `status`. Passwords, tokens, cookies, headers, CSRF
values, session values, and richer bridge results must not enter Sentinel DNA
arguments, logs, evidence, or provider options.

The bridge is validated before `browserAuth` is exposed. Missing or
unresolvable configuration returns `TB_AUTH_BRIDGE_MISSING`; a module without
`requestBrowserAuth()` returns `TB_AUTH_BRIDGE_EXPORT_INVALID`; and a bridge
load or execution error returns `TB_AUTH_BRIDGE_RUNTIME_FAILED`. Every result
is fail-closed. Test, fixture, mock, stub, and simulation modules are not
approved capabilities.

The checked-in provider boundary and browser facade perform the final origin,
surface, capability, and redaction checks. A provider must not rely on the
runner to make an unsafe runtime safe.

The repository's staging template contains the canonical checked-in facade and
provider-boundary paths. To apply those paths reproducibly in an operator
PowerShell scope, dot-source `scripts/configure_gate4_provider_environment.ps1`
with the separately reviewed runtime module, activation manifest, and reviewed
image digest. The helper does not set credentials or provide a runtime.

Before provider verification, the bridge contract can be checked with the
read-only acceptance harness:

```powershell
node .\deployment\staging\scripts\validate_trusted_browser_auth_bridge.mjs
```

The harness reads `SENTINEL_DNA_BROWSER_AUTH_BRIDGE`, imports the supplied
module only to validate its export, and never calls `requestBrowserAuth()`.
It emits only `PASS` or a fail-closed `BLOCKED_WITH_REASON` result. Structural
acceptance is not operator approval; the module must still come from approved
external custody.

## Runtime lifecycle

1. The operator configures the checked-in facade, provider boundary, and
   separately reviewed runtime module.
2. The verification command imports the modules and calls setup with only
   `{ environment: "codex-app" }`.
3. The provider returns the runtime; URL selection is limited to
   `https://uwakwe-desktop.taile388cc.ts.net`.
4. Verification creates one temporary tab to inspect the contract and closes
   it when possible. It never authenticates or invokes `browserAuth.request()`.
5. The pilot execution adapter performs its own browser contract and
   `browserAuth` preflight before the runner starts.
6. The operator follows the approved runtime's teardown and revocation
   procedure after verification or pilot execution.

## Trust assumptions

- The provider module is separately reviewed, locally supplied, and available
  only in the approved operator/trusted-browser runtime environment.
- The provider's Playwright/RPC transport is trusted and does not downgrade
  TLS, bypass origin validation, or expose a debugging endpoint.
- The runtime owns browser process and session lifecycle; Sentinel DNA does not
  persist browser sessions or credentials.
- The staging edge is private and uses the certified origin and approved TLS
  trust anchor.
- `browserAuth` remains an external operator-approved capability. Credentials
  are entered only through that capability and never become runner arguments,
  provider options, or evidence.

## Security restrictions

The following are prohibited:

- local standalone Playwright installation or launch as a provider substitute;
- direct CDP, browser-debugging-port, WebSocket, or alternate RPC connection;
- direct HTTP login automation or credential submission;
- credential, cookie, token, or session extraction or storage;
- arbitrary origins, redirects, hostnames, ports, or localhost bypasses;
- disabling origin, capability, redaction, or fail-closed checks;
- logging upstream exceptions, module paths, environment values, or secrets;
- using `tests/staging/fixtures/trusted-playwright-adapter-stub.mjs` for pilot
  execution.

## Exact operator configuration

From the repository root, configure the following non-secret module paths in
the approved operator environment. The third path must remain outside the
repository and must point to the separately reviewed runtime module:

```powershell
$env:SENTINEL_DNA_TRUSTED_BROWSER_CLIENT = "C:\Users\HP\Documents\sentinel-dna-postmerge-ssh\deployment\staging\scripts\trusted_browser_service\browser-client.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT = "C:\Users\HP\Documents\sentinel-dna-postmerge-ssh\deployment\staging\scripts\trusted_browser_service\providers\playwright-runtime-provider.mjs"
$env:SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME = "C:\approved\browser\playwright-runtime.mjs"
$env:SENTINEL_DNA_APPROVED_RUNTIME_DIGEST = "sha256:<64-hex-runtime-digest>"
$env:SENTINEL_DNA_BROWSER_AUTH_BRIDGE = "C:\approved\browser\browser-auth-bridge.mjs"
$env:SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST = "C:\approved\browser\trusted-browser-activation-manifest.json"
$env:SENTINEL_DNA_IMAGE_DIGEST = "sha256:<reviewed-64-hex-digest>"
$env:SENTINEL_DNA_ENV = "staging"
$env:SENTINEL_DNA_PILOT_ACCESS_REQUIRED = "1"
$env:SENTINEL_DNA_SECURE_COOKIES = "1"
$env:FLASK_DEBUG = "0"
$env:SENTINEL_DNA_TENANT_ISOLATION_ENABLED = "1"
$env:SENTINEL_DNA_AUDIT_LOGGING_ENABLED = "1"
```

The digest and control assertions are non-secret readiness inputs. The digest
must be the immutable reviewed staging image digest; do not put a real digest
in this repository document. The tenant-isolation and audit assertions must
also be enabled in the staging application deployment, not only in the
operator shell.

The activation manifest is a non-secret, integrity-checked JSON document held
outside the repository. Its required format is:

```json
{
  "schema_version": "1.0",
  "provider_identity": "reviewed-provider:provider-2026-09",
  "runtime_module_identity": "reviewed-runtime:runtime-2026-09",
  "approved_runtime_module_digest": "sha256:<64-hex-runtime-digest>",
  "approved_image_runtime_digest": "sha256:<64-hex-digest>",
  "staging_origin": "https://uwakwe-desktop.taile388cc.ts.net",
  "activation_timestamp": "2026-09-01T12:00:00Z",
  "operator_approval_reference": "APPROVAL-2026-09-001",
  "integrity": {
    "algorithm": "sha256",
    "manifest_hash": "<sha256-of-all-fields-except-integrity>"
  }
}
```

The manifest hash is verified before readiness can pass. If the approved
custody system uses a detached signature, it may add a `signature` object with
`scheme: "detached-external"`, a non-secret `key_reference`, and a
`signature_reference`; signing keys and signature-validation credentials must
remain outside this repository and runtime input.

The `approved_runtime_module_digest` must be the SHA-256 digest of the exact
external runtime module supplied to the operator host. Readiness recomputes
that digest and fails closed on absence or mismatch.

The configuration checker validates these variables and the referenced module
and manifest files without printing their values:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
```

The single operator activation gate then runs the provider report and all
readiness checks. It never mutates browser, runtime, or application state and
emits
only `READY_FOR_ANALYST_PILOT`, `BLOCKED_WITH_REASON`, and safe `TB_*` codes:

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -DryRun
```

When the operator environment is complete, normal activation writes a
non-secret report to `pilot-evidence/controlled-pilot-readiness-report-<timestamp>.json`.
The artifact uses exclusive creation and contains statuses only; it never
contains provider paths, credentials, cookies, tokens, or browser sessions.
Use `-DryRun` to perform the same validation without writing the report.

For safe remediation guidance without exposing configuration paths or runtime
exceptions, run:

```powershell
node .\deployment\staging\scripts\generate_trusted_browser_activation_troubleshooting_report.mjs
```

Verify the provider before any pilot execution:

```powershell
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
```

Proceed only when the JSON result has `"status": "PASS"` and every check is
`PASS`. The command's nonzero exit status is a fail-closed blocker.

## Failure states

The verifier and trusted browser chain return safe categories without paths,
credentials, environment secrets, or stack traces:

| Category | Meaning | Operator action |
| --- | --- | --- |
| `TB_PROVIDER_NOT_CONFIGURED` | Required provider/runtime path is absent | Configure the reviewed module path; do not guess a fallback |
| `TB_PROVIDER_MODULE_MISSING` | Configured local module cannot be loaded | Confirm the reviewed module is present and locally accessible |
| `TB_PROVIDER_EXPORT_INVALID` | Required `setupBrowserRuntime` export is absent | Return the module for provider review |
| `TB_RUNTIME_UNAVAILABLE` | Runtime setup or contract failed | Confirm the approved Playwright/RPC bridge; do not launch an alternate browser |
| `TB_BROWSER_SELECTION_FAILED` | Certified browser selection failed | Keep the pilot blocked and inspect the trusted runtime |
| `TB_BROWSER_CONTRACT_FAILED` | Browser/tab/Playwright/DOM surface is incomplete | Keep the pilot blocked; repair the reviewed provider contract |
| `TB_AUTH_CAPABILITY_MISSING` | External `browserAuth` capability is unavailable | Keep the pilot blocked; do not pass credentials another way |
| `TB_AUTH_BRIDGE_MISSING` | The reviewed browser authentication bridge is not configured or cannot be resolved | Supply the separately reviewed bridge module; do not use a fixture or alternate provider |
| `TB_AUTH_BRIDGE_EXPORT_INVALID` | The configured bridge does not export callable `requestBrowserAuth()` | Return the bridge for review and repair its interface |
| `TB_AUTH_BRIDGE_RUNTIME_FAILED` | The bridge failed to load or complete its browser-mediated handoff | Keep the pilot blocked and inspect the reviewed bridge without exposing its error or credentials |

Any unrecognized error is treated as the relevant safe category and remains a
blocker. Do not print the original exception or inspect it by adding logging.
