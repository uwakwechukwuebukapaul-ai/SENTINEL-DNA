# Gate 4 Operator Completion Plan

## Decision

Current decision: **BLOCKED**.

The Gate 4 repository implementation is complete. Deployment activation must
remain blocked until the external runtime and activation custody requirements
below are independently satisfied.

## Exact missing inputs

The approved operator or custody system must provide all of the following:

- Reviewed Playwright/RPC runtime module, installed only in the approved
  operator/trusted-browser environment.
- Runtime provenance metadata: supplier or release reference, module identity,
  version, review record, reviewer, review date, approved scope, and teardown
  owner.
- SHA-256 digest for the exact reviewed runtime artifact/module.
- Externally held Gate 4 activation custody manifest.
- Reviewer and human operator approval reference.
- Manifest integrity hash and exact binding to deployed image digest
  `sha256:17bf71b3ce57a3c1e3c6f840caa541a862cce74d6cfddc3dce9fd3d816e13653`.
- Manifest `approved_runtime_module_digest` equal to the exact runtime digest.
- Certified staging-origin validation for
  `https://sentinel-dna-staging:18443` over approved private TLS.
- Deployment evidence that secure cookies, debug-disabled mode, pilot access
  gating, tenant isolation, and audit logging are enabled.

The runtime and custody manifest are external artifacts. Do not create local
replacements, use the checked-in validation fixture, or install a standalone
browser runtime.

## Operator steps

1. Obtain the reviewed runtime and activation manifest through approved
   custody. Record only non-secret provenance, digest, review, approval,
   teardown, and scope metadata.
2. Verify the runtime artifact digest independently. Ensure the activation
   manifest contains the exact certified origin and image digest above, a
   valid SHA-256 canonical integrity hash, and the approval reference.
3. Configure the approved operator shell. The helper sets only non-secret
   environment values and rejects missing or repository-local artifacts:

   ```powershell
   . .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
     -ApprovedRuntimeModule 'C:\approved\browser\playwright-runtime.mjs' `
     -RuntimeDigest 'sha256:<64-hex-runtime-digest>' `
     -ActivationManifest 'C:\approved\browser\trusted-browser-activation-manifest.json' `
     -ImageDigest 'sha256:<64-hex-deployed-staging-image-digest>'
   ```

4. Run configuration validation:

   ```powershell
   .\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
   ```

   Expected output includes `STATUS=PASS` and the provider-configuration
   security assertions.

5. Verify external artifact custody and digest bindings:

   ```powershell
   node .\deployment\staging\scripts\verify_gate4_external_artifacts.mjs
   ```

   Expected completion result is provider `PASS` and activation
   `READY_FOR_ANALYST_PILOT` with `codes: []`. With missing artifacts the
   command must remain blocked and list only safe `TB_*` codes.

6. Verify the trusted browser provider before any pilot activity:

   ```powershell
   node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
   ```

   Expected result:

   ```json
   {
     "status": "PASS",
     "checks": {
       "provider": "PASS",
       "runtime": "PASS",
       "origin": "PASS",
       "browser_contract": "PASS",
       "browser_auth": "PASS"
     }
   }
   ```

   Verification discovers `browserAuth` but does not call
   `browserAuth.request()`.

7. Run activation and readiness validation:

   ```powershell
   .\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
   node .\deployment\staging\scripts\check_controlled_pilot_readiness.mjs
   ```

   Expected activation result is exactly:

   ```json
   {"status":"READY_FOR_ANALYST_PILOT","codes":[]}
   ```

   The readiness result must be `READY_FOR_ANALYST_PILOT` and every check must
   be `PASS`. Any `BLOCKED_WITH_REASON` result is final for that attempt.

8. Generate non-secret provider/readiness evidence:

   ```powershell
   node .\deployment\staging\scripts\generate_gate4_evidence.mjs
   node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
   ```

   Preserve evidence only under approved append-only custody. Do not preserve
   credentials, cookies, tokens, browser sessions, customer data, or raw
   upstream exceptions.

9. After human release approval, run the controlled pilot with a non-secret
   operator run ID and validate its resulting evidence:

   ```powershell
   node .\deployment\staging\scripts\run_controlled_analyst_pilot.mjs <operator-run-id>
   node .\deployment\staging\scripts\validate_manual_analyst_pilot_evidence.mjs <evidence-file>
   ```

## Safe blocker diagnostics

`TB_RUNTIME_UNAVAILABLE` means the reviewed external runtime or its trusted
RPC bridge is unavailable or failed its contract. Confirm custody, module
identity, digest, installation scope, and reviewed runtime lifecycle. Do not
launch standalone Playwright, use CDP, or connect to an alternate endpoint.

`TB_PROVIDER_MANIFEST_MISSING` means the external activation manifest is not
configured or cannot be loaded. Obtain it from approved custody and verify its
integrity, approval reference, certified origin, and image digest. Do not use
the checked-in validation fixture as an activation artifact.

Diagnostics expose only the allowlisted code, artifact class, configuration
variable, and next action. They do not print paths, secrets, credentials,
provider exceptions, or browser state.

## Rollback procedure

If any validation fails, an unexpected access occurs, evidence is incomplete,
or the runtime behaves outside its reviewed contract:

1. Stop pilot activity and record the non-secret run ID and UTC time.
2. Keep Gate 4 blocked and notify the security/release owner.
3. Revoke the pilot authorization through the approved control plane.
4. Invalidate active analyst sessions and verify post-revocation access fails
   closed. Do not collect or copy session or credential material.
5. Stop or tear down the external browser runtime through its reviewed
   lifecycle procedure; do not kill, reconnect, or recover through an
   unapproved endpoint.
6. Preserve only non-secret audit references, evidence hashes, provenance, and
   incident/approval references in approved custody.
7. Re-run the complete readiness process and obtain new human approval before
   any reactivation.
