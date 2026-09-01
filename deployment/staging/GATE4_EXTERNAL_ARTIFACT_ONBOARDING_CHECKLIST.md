# Gate 4 External Artifact Onboarding Checklist

Use this checklist on the approved private staging/operator host. It is an
intake and verification record for non-secret artifact metadata. Do not place
credentials, cookies, tokens, signing keys, browser sessions, or runtime state
in Git or in Gate 4 evidence.

Gate 4 remains `BLOCKED_WITH_REASON` until every required item below is
verified with genuine external custody and staging evidence. A checked-in
fixture, mock, browser substitute, or simulation result cannot satisfy this
checklist.

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

## Activation readiness evidence

- [ ] Runtime module: exact reviewed module is present on the approved host and
      exports the reviewed runtime contract.
- [ ] Runtime SHA-256: digest is independently calculated for that exact
      module and matches the custody record and manifest.
- [ ] Activation manifest: current approved manifest is held in external
      custody and passes schema, integrity, approval, and runtime binding.
- [ ] Image digest binding: manifest digest exactly matches the immutable
      deployed staging image digest.
- [ ] Origin validation: private-TLS reachability is verified for exactly
      `https://sentinel-dna-staging:18443`.
- [ ] Tenant isolation evidence: staging evidence demonstrates tenant
      separation and cross-tenant denial without retaining customer data.
- [ ] Audit evidence: audit logging, evidence/provenance sinks, and the
      resulting non-secret audit references are available under approved
      custody.

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

The onboarding command writes a new exclusive-create evidence file under
`pilot-evidence/gate4/` (the default name contains the current UTC timestamp;
use `--output` for an approved unique name). It contains statuses, digests,
safe codes, and control assertions only.

## Safe blocker handling

`TB_RUNTIME_UNAVAILABLE` means the reviewed runtime is absent, unreadable,
unavailable, or its setup/RPC/browser contract failed. Obtain the exact
reviewed artifact and rerun the sequence. A digest mismatch is reported as
`TB_PROVIDER_MANIFEST_INVALID`.

`TB_PROVIDER_MODULE_MISSING` means the configured reviewed provider/client
module is absent or cannot be loaded. Restore the reviewed module from its
approved package; do not point the variable at a test fixture.

`TB_PROVIDER_MANIFEST_MISSING` means the custody manifest is absent or not
configured. Obtain the approved manifest and configure it through the helper.

`TB_PROVIDER_MANIFEST_INVALID` means schema, integrity, origin, approval, image
binding, or runtime digest reconciliation failed. Return the manifest to
custody for correction; never hand-edit evidence.

`TB_ORIGIN_UNREACHABLE` means the certified staging origin could not be
validated from the approved host. Keep activation blocked and repair the
approved private-TLS/network path; do not use another origin or bypass TLS.

Any blocker keeps analyst activation closed. Provider verification must be
`PASS` and activation must be `READY_FOR_ANALYST_PILOT` with `codes: []` before
human release approval and pilot execution.
