# Gate 4 Deterministic Operator Runbook

This runbook is executed only on the approved private staging/operator host.
It does not install a browser, create a provider, handle credentials, or
override a failed check.

Complete [`GATE4_EXTERNAL_ARTIFACT_ONBOARDING_CHECKLIST.md`](GATE4_EXTERNAL_ARTIFACT_ONBOARDING_CHECKLIST.md)
alongside this runbook. The current Gate 4 decision is **BLOCKED**. The
runbook prepares activation; it does not create or accept external custody
artifacts.

## 1. Obtain the approved runtime

Obtain the separately reviewed Playwright/RPC runtime module from the approved
internal distribution or custody system. Do not obtain it by adding a
repository dependency, installing standalone Playwright, using a test fixture,
or connecting to CDP/debugging ports.

Record outside Git, without secrets:

- runtime module identity and version;
- supplier/release and security review reference;
- reviewer and review date;
- exact artifact SHA-256 digest;
- approved staging image/runtime scope;
- trusted RPC and teardown/revocation procedure;
- runtime custody owner and incident contact.

## 2. Validate runtime provenance

Independently verify that the digest is for the exact reviewed module supplied
to the operator host. Reconcile it with the external review/custody record.
Do not place the runtime module, credentials, signing keys, or session state in
this repository.

The module must export `setupBrowserRuntime({ environment })`, accept only
`environment: "codex-app"`, and return `browsers.getForUrl(origin)`. The
selected browser must provide the reviewed tab and `browserAuth` contract.

## 3. Generate and approve the activation manifest

Create the manifest through the approved custody/approval workflow, outside
Git. It must contain:

- schema version `1.0`;
- reviewed provider and runtime identities;
- image digest
  `sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653`;
- exact origin `https://sentinel-dna-staging:18443`;
- UTC activation timestamp;
- reviewer/operator approval reference;
- SHA-256 canonical integrity hash;
- externally validated detached signature metadata, if required.

Canonicalize recursively by sorted object keys, preserve array order, omit the
`integrity` object while hashing, and hash the UTF-8 JSON payload without added
whitespace or a newline. Never hand-edit a readiness report to reconcile a
digest mismatch.

## 4. Configure non-secret operator inputs

From the repository root, dot-source the helper with the external artifacts:

```powershell
. .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
  -ApprovedRuntimeModule 'C:\approved\browser\playwright-runtime.mjs' `
  -ActivationManifest 'C:\approved\browser\trusted-browser-activation-manifest.json' `
  -ImageDigest 'sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653'
```

Expected success output includes `STATUS=PASS`. Missing artifacts must instead
produce `STATUS=BLOCKED_WITH_REASON` with the safe variable, artifact class,
diagnostic, and next action. No path or secret should be printed.

## 5. Verify the certified origin and deployment evidence

Confirm the approved private TLS path reaches exactly
`https://sentinel-dna-staging:18443`. Confirm the deployed service, not merely
the operator shell, has secure cookies, debug disabled, pilot access gating,
tenant isolation, audit logging, synthetic-only scope, and no production data
or public exposure.

Retain non-secret tenant-isolation evidence (including cross-tenant denial) and
audit evidence (including the audit/evidence sink references) under approved
custody. Environment flags alone do not replace that evidence.

## 6. Run validation in order

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
node .\deployment\staging\scripts\verify_gate4_external_artifacts.mjs
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
node .\deployment\staging\scripts\check_controlled_pilot_readiness.mjs
node .\deployment\staging\scripts\generate_gate4_evidence.mjs
node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
```

Expected provider result:

```json
{"status":"PASS"}
```

Every provider sub-check must also be `PASS`. Expected activation result:

```json
{"status":"READY_FOR_ANALYST_PILOT","codes":[]}
```

The readiness report must be `READY_FOR_ANALYST_PILOT` with all checks `PASS`.
Provider verification discovers `browserAuth` but does not invoke it.

The four relevant blocker mappings are:

| Condition | Diagnostic | Required action |
| --- | --- | --- |
| Reviewed provider/client module is absent or unloadable | `TB_PROVIDER_MODULE_MISSING` | Restore the reviewed provider module from approved custody. |
| Reviewed runtime module, runtime setup, RPC bridge, or runtime contract is unavailable | `TB_RUNTIME_UNAVAILABLE` | Restore/reconcile the reviewed runtime and rerun its custody-bound checks. |
| Activation custody manifest is absent or not configured | `TB_PROVIDER_MANIFEST_MISSING` | Obtain the external approved manifest; never use the checked-in fixture. |
| Exact certified origin cannot be reached over approved private TLS | `TB_ORIGIN_UNREACHABLE` | Repair the approved staging path and validate `https://sentinel-dna-staging:18443`. |

Manifest content or digest mismatches are `TB_PROVIDER_MANIFEST_INVALID`, and
an origin value inside a manifest that is not the exact certified origin is
`TB_ORIGIN_REJECTED`. Any one of these diagnostics keeps activation blocked.

Only after human release approval:

```powershell
node .\deployment\staging\scripts\run_controlled_analyst_pilot.mjs <operator-run-id>
node .\deployment\staging\scripts\validate_manual_analyst_pilot_evidence.mjs <evidence-file>
```

## 7. Safe blocker handling

`TB_RUNTIME_UNAVAILABLE` means the reviewed runtime or trusted RPC bridge is
absent, unavailable, or contract-invalid. Keep the pilot blocked and consult
the runtime custody owner. Do not substitute a local runtime.

`TB_PROVIDER_MODULE_MISSING` means a reviewed provider/client module is absent
or cannot be loaded. Restore the reviewed module from approved custody.

`TB_PROVIDER_MANIFEST_MISSING` means the external activation manifest is not
configured or cannot be loaded. Obtain it from approved custody and rerun the
manifest/readiness checks. Do not use the checked-in validation fixture.

`TB_ORIGIN_UNREACHABLE` means the exact certified origin is unavailable from
the approved host. Keep the gate blocked and repair private-TLS reachability;
do not use an alternate origin, localhost, CDP, or a browser mock.

## 8. Rollback

On any failed control, unexpected access, runtime anomaly, evidence problem, or
pilot stop condition:

1. Stop pilot activity and record the non-secret run ID and UTC time.
2. Keep activation blocked and notify the security/release owner.
3. Revoke the pilot authorization through the approved control plane.
4. Invalidate analyst sessions and verify post-revocation denial.
5. Tear down the external runtime through its reviewed lifecycle procedure.
6. Preserve only non-secret audit, provenance, approval, incident, and evidence
   hashes under approved custody.
7. Re-run the complete readiness sequence and obtain fresh human approval
   before reactivation.
