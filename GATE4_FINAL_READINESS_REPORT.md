# Sentinel DNA Gate 4 Final Readiness Report

Audit date: 2026-09-01
Repository: `SENTINEL-DNA`
Branch: `gate4-controlled-analyst-pilot`
Commit: `bcfd3960bc013b079d5fa373eca6e8bafd109ebf`
Image digest: `sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653`

## Executive Status

**BLOCKED**

The Sentinel DNA Gate 4 implementation is **COMPLETE**. Deployment activation
for the controlled analyst pilot is **BLOCKED** because the externally owned
approved Playwright/RPC runtime and activation-custody manifest are not
available. No local replacement, mock, bypass, or credential path was added.

This is a controlled external-dependency block, not a repository security
failure.

## Architecture Assessment

**PASS - provider boundary:**

- `trusted_browser_service/browser-client.mjs` is the reviewed facade.
- `providers/playwright-runtime-provider.mjs` is the checked-in provider
  boundary and forwards only `environment: "codex-app"` to the external
  runtime.
- `trusted_browser_execution_adapter.mjs` creates the browser only through the
  configured trusted chain and performs a browser/tab contract preflight.
- The external runtime remains operator-owned and is not installed, launched,
  or simulated by this repository.

**PASS - browser contract and origin controls:**

- Browser selection is restricted to the exact certified HTTPS origin
  `https://sentinel-dna-staging:18443`.
- Navigation, browser selection, and activation manifest validation reject
  alternate origins, credentials in URLs, paths, queries, fragments, and
  unapproved runtime inputs.
- Required surfaces are enforced: `tabs.new`, `goto`, Playwright locator and
  evaluation, visible DOM inspection, and capability discovery.

**PASS - browserAuth and fail-closed behavior:**

- `browserAuth` is mandatory and remains an external operator-approved
  capability.
- Provider verification discovers the capability but does not invoke
  `browserAuth.request()`.
- Missing providers, invalid exports, unavailable runtimes, failed browser
  selection, incomplete contracts, and missing browserAuth produce safe
  `TB_*` blockers and stop execution.

**PASS - redaction and evidence model:**

- Secret-shaped fields are rejected from provider input and removed from DOM,
  evaluation, and browserAuth results.
- Upstream exceptions, paths, environment values, credentials, cookies,
  tokens, and sessions are not exposed across the reviewed boundaries.
- Evidence generation is status-only, deterministic, and uses exclusive file
  creation; it does not launch a browser, connect to CDP, navigate, or
  authenticate.

## Security Assessment

**PASS.** The audited controls preserve the Gate 4 security posture:

- No direct credential handling was introduced.
- No standalone Playwright, fake provider, mock runtime, CDP/debugging-port,
  localhost bypass, direct HTTP login, or origin-check bypass exists in the
  Gate 4 activation path.
- The controlled pilot wrapper checks readiness before browser creation.
- Configuration validation pins the checked-in facade/provider boundary and
  the improved environment helper rejects repository-local runtime and
  manifest artifacts.
- The activation manifest validator enforces schema, safe identities, UTC
  timestamp, exact origin, SHA-256 integrity, and image-digest format.

## Evidence Assessment

**PASS - evidence is present and non-secret.** The following artifacts were
generated or reviewed under `pilot-evidence/gate4/`:

- `gate4-provider-verification-20260901.json`: provider boundary passes;
  runtime fails closed with `TB_RUNTIME_UNAVAILABLE`; browserAuth was not
  invoked.
- `gate4-readiness-audit-20260901.json`: formal Gate 4 audit with the required
  Git revision, tree, immutable image digest, checks, blockers, and
  remediation.
- `gate4-activation-validation-20260901.json`: activation custody validation
  blocked because the external manifest is not configured.

The checked-in `trusted-browser-activation-manifest.json` is explicitly a
schema/integrity validation fixture, not an operator approval artifact. It
cannot satisfy external activation custody. No runtime module, browser session,
credential, token, cookie, or secret is committed in the Gate 4 evidence.

The audited immutable image identity is:

`sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653`

## Remaining External Dependencies

1. The separately reviewed Playwright/RPC runtime module must be supplied from
   approved custody, with provenance, reviewer, immutable runtime digest,
   scope, and teardown ownership recorded.
2. The externally held activation manifest must be supplied with valid
   integrity, exact certified origin, operator approval reference, and the
   image digest above.
3. The approved staging operator host must confirm private TLS reachability,
   tenant isolation, audit logging, secure cookies, pilot access gating, and
   debug-disabled deployment assertions.

## Exact Operator Actions Required

On the approved operator host:

1. Obtain the reviewed runtime and activation manifest through the approved
   custody workflow. Do not create either artifact locally.
2. Record runtime provenance/custody and human approval without recording
   credentials or browser-session material.
3. Configure the environment using the helper below, substituting only the
   approved external artifact paths:

   ```powershell
   . .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
     -ApprovedRuntimeModule 'C:\approved\browser\playwright-runtime.mjs' `
     -ActivationManifest 'C:\approved\browser\trusted-browser-activation-manifest.json' `
     -ImageDigest 'sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653'
   ```

4. Run the configuration dry run, provider verification, and activation check:

   ```powershell
   .\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
   node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
   .\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
   ```

5. Continue only when provider verification is fully `PASS` and activation
   returns `{"status":"READY_FOR_ANALYST_PILOT","codes":[]}`. Then obtain
   the required human release approval, run the controlled pilot, and generate
   final evidence.

## Release Recommendation

**Do not activate or release the controlled analyst pilot yet.** Keep Gate 4
blocked until the external runtime, activation manifest, custody records, and
approved staging-host prerequisites are verified. Once those external gates
pass, the repository implementation is suitable to proceed to the controlled
analyst pilot without code changes.

Validation summary: Gate 4 Node tests **58 passed**; staging Python tests
**38 passed**; PowerShell helper syntax validation **passed**; provider
verification correctly returned the expected controlled `TB_RUNTIME_UNAVAILABLE`
block when the checked-in boundary was configured without the external runtime.
