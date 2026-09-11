# Gate 4 External Artifact Onboarding Report

## Status

**BLOCKED_WITH_REASON**

The repository-owned onboarding verifier and fail-closed runtime digest
enforcement are complete. This workspace does not contain the real reviewed
Playwright/RPC runtime or the externally held activation custody manifest, so
Gate 4 is not ready for analyst access.

## Required external inputs

- Reviewed Playwright/RPC runtime module.
- Runtime provenance metadata and reviewer approval reference.
- SHA-256 digest of the exact runtime module.
- Activation custody manifest with `approved_runtime_module_digest`.
- Manifest canonical integrity hash and immutable image digest binding.
- Certified staging origin validation and operator approval.

## Verification contract

`verify_gate4_external_artifacts.mjs` verifies runtime existence, runtime
digest-to-manifest binding, manifest integrity, image digest binding, certified
origin binding, and the existing provider verification chain. It never invokes
`browserAuth`, handles credentials, launches a local browser, connects to CDP,
or stores session state.

## Current safe blockers

- `TB_RUNTIME_UNAVAILABLE`: no approved external runtime is configured in this
  operator workspace.
- `TB_PROVIDER_MANIFEST_MISSING`: no approved external activation custody
  manifest is configured in this operator workspace.

The checked-in manifest and test fixtures remain non-authoritative and cannot
activate the pilot. Supply real custody artifacts, run the checklist, and
retain only the generated non-secret JSON evidence.

## Remediation

1. Obtain the reviewed runtime and provenance record from approved custody.
2. Verify and record its SHA-256 digest outside Git.
3. Obtain the approved activation manifest, reconcile runtime and image
   digests, and validate its canonical integrity hash.
4. Configure both artifacts with the operator helper.
5. Run onboarding, provider, activation, and readiness checks in order.
6. Proceed only when provider status is `PASS` and activation is
   `{"status":"READY_FOR_ANALYST_PILOT","codes":[]}`.
