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

The dated audit artifacts below are retained historical records of earlier
controlled blockers:

- `gate4-provider-verification-20260901.json`
- `gate4-readiness-audit-20260901.json`
- `gate4-activation-validation-20260901.json`
- `gate4-external-artifact-verification-20260901.json`

The current non-secret handoff evidence is:

- `gate4-provider-verification-20260902-final.json` — provider, runtime,
  certified-origin, browser-contract, and browser-auth verification passed;
- `gate4-external-artifact-verification-20260902T163527Z.json` — external
  runtime, dependency, manifest, image, bridge, and origin bindings passed;
- `gate4-controlled-pilot-readiness-20260902.json` — deterministic 13-check
  readiness reference bound to source commit
  `b24d0cf5dad78f9848ed1300d48236e48092e3e9`, with evidence SHA-256
  `b623171257833c536a5ae3c6c82a8a75768c1f3b67a708460c645a9b8434dd00`.

These records do not contain credentials, tokens, cookies, sessions, private
keys, or runtime bundles. The external activation manifest and runtime remain
in approved custody; the checked-in manifest is only a validation fixture.

The operator intake and activation procedure are documented in
[`deployment/staging/GATE4_EXTERNAL_ARTIFACT_ONBOARDING_CHECKLIST.md`](../../deployment/staging/GATE4_EXTERNAL_ARTIFACT_ONBOARDING_CHECKLIST.md)
and [`deployment/staging/GATE4_OPERATOR_RUNBOOK.md`](../../deployment/staging/GATE4_OPERATOR_RUNBOOK.md).

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

The verifier uses a fresh UTC-stamped output filename by default, or an
approved unique `--output` filename. Historical evidence is never overwritten.

The generator never authenticates, invokes `browserAuth`, launches a local
browser, connects to CDP, or writes credentials. It exits nonzero when any
trusted-browser check is blocked.
