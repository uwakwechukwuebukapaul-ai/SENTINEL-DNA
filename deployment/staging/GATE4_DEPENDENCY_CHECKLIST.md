# Gate 4 Final Dependency Checklist

Gate 4 is **BLOCKED** until all three ownership classes below are complete.
The repository implementation is complete; this checklist tracks activation
inputs and custody evidence. No item may be satisfied with a mock, fixture,
local browser substitute, or unreviewed provider.

## Repository-owned requirements

- [x] Trusted browser facade is present and origin-scoped.
- [x] Provider boundary forwards only `environment: "codex-app"`.
- [x] Runtime adapter requires the reviewed provider chain and browser
      contract.
- [x] Exact certified origin is enforced:
      `https://sentinel-dna-staging:18443`.
- [x] `browserAuth` capability is required and credentials remain external.
- [x] Secret-shaped input/output redaction and safe diagnostics are enforced.
- [x] Activation manifest schema, integrity, origin, timestamp, and digest
      validation are present.
- [x] Pilot runner checks readiness before browser creation and records
      tenant, denial, audit, provenance, and revocation gates.
- [x] Evidence generation is deterministic, non-secret, and exclusive-create.
- [x] External artifact onboarding verifier checks runtime existence, runtime
      digest binding, manifest integrity, image binding, and provider status.
- [x] Gate 4 Node and staging Python tests pass.

## Operator-owned requirements

- [ ] Approved operator host is configured for staging only.
- [ ] Checked-in facade and provider boundary are configured at their reviewed
      module identities.
- [ ] `SENTINEL_DNA_IMAGE_DIGEST` equals the deployed immutable image digest:
      `sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653`.
- [ ] `SENTINEL_DNA_ENV=staging` and all required security assertions are
      enabled in the deployed service.
- [ ] Certified origin is reachable over approved private TLS.
- [ ] Tenant isolation and cross-tenant denial are verified in staging.
- [ ] Audit logging and evidence/provenance sinks are available and writable
      under approved custody.
- [ ] Human release approval is recorded before analyst access is issued.

## External custody requirements

- [ ] Separately reviewed Playwright/RPC runtime module is supplied.
- [ ] Runtime provenance metadata identifies supplier/release, module version,
      review reference, reviewer, review date, scope, and teardown owner.
- [ ] SHA-256 digest of the exact runtime artifact is verified and recorded.
- [ ] Activation manifest is held outside the repository in approved custody.
- [ ] Manifest contains the exact certified origin and deployed image digest.
- [ ] Manifest canonical integrity hash validates with SHA-256.
- [ ] Reviewer and operator approval reference is present and current.
- [ ] Detached signature metadata is validated by the external custody system,
      when required; signing keys never enter the repository or runtime input.

## Required blocked behavior before completion

- [ ] Provider verification remains `BLOCKED_WITH_REASON` with
      `TB_RUNTIME_UNAVAILABLE` when the real runtime is absent.
- [ ] Activation validation remains `BLOCKED_WITH_REASON` with
      `TB_PROVIDER_MANIFEST_MISSING` when the custody manifest is absent.
- [ ] No pilot browser session is created while readiness is blocked.

## Completion evidence

After the real artifacts are supplied, retain only non-secret evidence showing:

1. runtime provenance and digest verification;
2. activation manifest integrity, origin, approval, and image binding;
3. provider verification with every check `PASS`;
4. activation result `{"status":"READY_FOR_ANALYST_PILOT","codes":[]}`;
5. human release approval and controlled pilot evidence validation.

The deterministic onboarding command is:

```powershell
node .\deployment\staging\scripts\verify_gate4_external_artifacts.mjs
```
