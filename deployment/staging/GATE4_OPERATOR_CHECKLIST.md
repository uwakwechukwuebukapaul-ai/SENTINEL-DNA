# Gate 4 Controlled Analyst Pilot Operator Checklist

This checklist is for the approved staging operator only. Gate 4 remains
blocked unless every prerequisite and command succeeds. Do not substitute a
test fixture, standalone Playwright process, CDP/debugging endpoint, direct
HTTP login, credential environment variable, or localhost origin.

## Prerequisites

- [ ] The approved browser runtime module exists in external reviewed custody.
- [ ] The integrity-checked activation manifest exists in external approved
      custody.
- [ ] The runtime artifact/module digest has been independently verified and
      reconciled with the deployed immutable staging image digest.
- [ ] The exact certified staging origin is reachable over approved private
      TLS: `https://sentinel-dna-staging:18443`.
- [ ] Operator approval and the human release reference are recorded outside
      the repository.
- [ ] Tenant isolation, audit logging, secure cookies, pilot access gating, and
      debug-disabled assertions are enabled in the deployed staging service.
- [ ] No credentials, cookies, tokens, private keys, browser sessions, or
      customer data are present in the repository or evidence directory.

Configure only non-secret paths and the reviewed image digest. The helper
rejects missing artifacts and repository-local runtime/manifest files:

```powershell
. .\deployment\staging\scripts\configure_gate4_provider_environment.ps1 `
  -ApprovedRuntimeModule 'C:\approved\browser\playwright-runtime.mjs' `
  -RuntimeDigest 'sha256:<64-hex-runtime-digest>' `
  -ActivationManifest 'C:\approved\browser\trusted-browser-activation-manifest.json' `
  -ImageDigest 'sha256:<64-hex-deployed-staging-image-digest>'
```

## Validation commands

Run from the repository root on the approved operator host.

### Verify provider

```powershell
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
```

Require `status: "PASS"` and `PASS` for provider, runtime, origin,
browser-contract, and browser-auth checks. Verification discovers
`browserAuth`; it does not invoke it.

### Check activation

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

Require exactly `{"status":"READY_FOR_ANALYST_PILOT","codes":[]}` from the
activation check. Any `BLOCKED_WITH_REASON` result is final for that attempt.

### Run controlled pilot

```powershell
node .\deployment\staging\scripts\run_controlled_analyst_pilot.mjs <operator-run-id>
```

Use only an operator-assigned non-secret run identifier. Stop immediately on
any failed, not-measured, unexpected, cross-tenant, privileged, audit, or
provenance check. Follow the approved runtime teardown and revocation process.

### Generate evidence

```powershell
node .\deployment\staging\scripts\generate_gate4_evidence.mjs
node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
```

Preserve only non-secret JSON evidence under approved append-only custody.
Confirm that evidence contains no credentials, cookies, tokens, session values,
customer data, provider exceptions, or browser-session material.

## Stop and escalate

Keep Gate 4 blocked for a missing runtime, missing manifest, digest mismatch,
unreachable certified origin, missing `browserAuth`, failed tenant isolation,
failed audit/provenance checks, or unavailable evidence custody. Escalate to
the runtime/security owner for the approved artifact or custody correction;
never bypass the failing control.
