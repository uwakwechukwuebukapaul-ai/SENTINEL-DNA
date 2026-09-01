# Gate 4 evidence

This directory contains non-secret, deterministic evidence for the trusted
browser provider gate.

`trusted-browser-activation-manifest.json` is a non-secret schema/integrity
validation fixture only. It is not an operator approval artifact and must not
be used to activate the pilot. The authoritative activation manifest must be
held in approved external custody and supplied through
`SENTINEL_DNA_TRUSTED_BROWSER_ACTIVATION_MANIFEST`. The operator-supplied
Playwright runtime remains a required external input through
`SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME`; neither artifact is replaced or
simulated by this repository.

The dated audit artifacts record the current controlled blocker:

- `gate4-provider-verification-20260901.json`
- `gate4-readiness-audit-20260901.json`
- `gate4-activation-validation-20260901.json`
- `gate4-external-artifact-verification-20260901.json`

Generate the provider evidence after configuring the operator runtime:

```powershell
. .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
  -ApprovedRuntimeModule 'C:\approved\browser\playwright-runtime.mjs' `
  -ActivationManifest 'C:\approved\browser\trusted-browser-activation-manifest.json' `
  -ImageDigest 'sha256:<reviewed-64-hex-digest>'
node .\deployment\staging\scripts\generate_gate4_evidence.mjs
```

Verify external artifact custody and digest bindings with:

```powershell
node .\deployment\staging\scripts\verify_gate4_external_artifacts.mjs
```

The generator never authenticates, invokes `browserAuth`, launches a local
browser, connects to CDP, or writes credentials. It exits nonzero when any
trusted-browser check is blocked.
