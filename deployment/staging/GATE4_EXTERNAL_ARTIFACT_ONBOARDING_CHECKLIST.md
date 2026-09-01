# Gate 4 External Artifact Onboarding Checklist

Use this checklist on the approved private staging/operator host. It is an
intake and verification record for non-secret artifact metadata. Do not place
credentials, cookies, tokens, signing keys, browser sessions, or runtime state
in Git or in Gate 4 evidence.

## Receive and record outside Git

- [ ] Approved Playwright/RPC runtime module received from reviewed custody.
- [ ] Runtime provenance received: supplier/release, module identity/version,
      security review reference, reviewer/date, approved scope, custody owner,
      teardown/revocation owner.
- [ ] Runtime SHA-256 digest calculated for the exact received module and
      reconciled to the custody record.
- [ ] Activation manifest received from approved custody, not copied from the
      repository fixture.
- [ ] Manifest approval reference is current and maps to the reviewed runtime,
      image, origin, and operator approval.
- [ ] Manifest contains `approved_runtime_module_digest` equal to the exact
      runtime artifact digest.
- [ ] Manifest contains the immutable deployed image digest and certified
      origin `https://sentinel-dna-staging:18443`.
- [ ] Manifest canonical SHA-256 integrity hash validates.

## Configure non-secret inputs

```powershell
. .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
  -ApprovedRuntimeModule 'C:\approved\custody\reviewed-runtime.mjs' `
  -ActivationManifest 'C:\approved\custody\activation-manifest.json' `
  -ImageDigest 'sha256:<64-hex-deployed-image-digest>'
```

The helper prints only `PASS`, an artifact class, a safe variable name, a
`TB_*` diagnostic, and a next action. A failure is authoritative; do not
replace the artifact with a fixture or local browser.

## Validation sequence

```powershell
node .\deployment\staging\scripts\verify_gate4_external_artifacts.mjs
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
node .\deployment\staging\scripts\check_controlled_pilot_readiness.mjs
node .\deployment\staging\scripts\generate_gate4_evidence.mjs
```

Expected completion output is both of the following, with no codes:

```json
{"status":"PASS"}
{"status":"READY_FOR_ANALYST_PILOT","codes":[]}
```

The onboarding evidence is written to
`pilot-evidence/gate4/gate4-external-artifact-verification-20260901.json`.
It contains statuses, digests, safe codes, and control assertions only.

## Safe blocker handling

`TB_RUNTIME_UNAVAILABLE` means the reviewed runtime is absent, unreadable,
unavailable, or does not match the custody-bound digest. Obtain the exact
reviewed artifact and rerun the sequence.

`TB_PROVIDER_MANIFEST_MISSING` means the custody manifest is absent or not
configured. Obtain the approved manifest and configure it through the helper.

`TB_PROVIDER_MANIFEST_INVALID` means schema, integrity, origin, approval, image
binding, or runtime digest reconciliation failed. Return the manifest to
custody for correction; never hand-edit evidence.

Any blocker keeps analyst activation closed. Provider verification must be
`PASS` and activation must be `READY_FOR_ANALYST_PILOT` with `codes: []` before
human release approval and pilot execution.
