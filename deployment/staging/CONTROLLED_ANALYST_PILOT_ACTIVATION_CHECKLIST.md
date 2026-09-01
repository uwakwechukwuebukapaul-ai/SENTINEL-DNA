# Controlled Analyst Pilot Activation Checklist

This is the final operator checklist for one bounded, non-production Sentinel
DNA controlled analyst pilot. It authorizes no account creation, credential
issuance, endpoint publication, or production access. Any unchecked item is
`BLOCKED_WITH_REASON`.

## 1. External reviewed runtime

- [ ] Obtain the separately reviewed Playwright/RPC runtime package through
  the approved operator distribution channel.
- [ ] Verify the runtime package identity and immutable SHA-256 digest against
  the security review record.
- [ ] Confirm the runtime owns browser lifecycle and the trusted RPC bridge.
- [ ] Confirm the runtime exports only the reviewed
  `setupBrowserRuntime({ environment })` boundary required by the provider
  contract.
- [ ] Confirm no standalone Playwright launch, CDP endpoint, debugging port,
  direct HTTP login client, or credential-bearing option is used.
- [ ] Keep runtime installation, signing keys, credentials, cookies, tokens,
  and browser sessions outside this repository.

## 2. Provider module registration

- [ ] Set `SENTINEL_DNA_TRUSTED_BROWSER_CLIENT` to the checked-in trusted
  browser facade.
- [ ] Set `SENTINEL_DNA_TRUSTED_BROWSER_UPSTREAM_CLIENT` to the checked-in
  reviewed provider boundary.
- [ ] Set `SENTINEL_DNA_APPROVED_PLAYWRIGHT_RUNTIME` to the external reviewed
  runtime module.
- [ ] Confirm none of the configured paths points to `tests/staging/` or a
  test-only adapter.
- [ ] Run provider verification and require every provider check to pass.

## 3. Activation manifest

- [ ] Create the manifest through the approved custody or signing workflow;
  do not create it from a test fixture.
- [ ] Include provider identity, runtime module identity, approved image/runtime
  digest, certified staging origin, UTC activation timestamp, and operator
  approval reference.
- [ ] Compute `integrity.manifest_hash` as SHA-256 over the canonical manifest
  payload excluding the `integrity` object.
- [ ] Keep the manifest outside Git and exclude paths, credentials, cookies,
  tokens, and session values.
- [ ] If detached signing is used, verify it through the external approved
  custody system; never place signing keys in this repository.

## 4. Image and origin reconciliation

- [ ] Set `SENTINEL_DNA_IMAGE_DIGEST` to the immutable reviewed staging image
  digest.
- [ ] Confirm the manifest digest exactly matches `SENTINEL_DNA_IMAGE_DIGEST`.
- [ ] Confirm `SENTINEL_DNA_ENV=staging`.
- [ ] Confirm the manifest origin is exactly
  `https://sentinel-dna-staging:18443`.
- [ ] Confirm the origin is reachable over TLS using the approved trust anchor.
- [ ] Reject redirects, alternate hostnames, alternate ports, localhost, and
  public listeners.

## 5. Security and custody prerequisites

- [ ] Set `SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1`.
- [ ] Set `SENTINEL_DNA_SECURE_COOKIES=1`.
- [ ] Set `FLASK_DEBUG=0`.
- [ ] Set `SENTINEL_DNA_TENANT_ISOLATION_ENABLED=1` and verify the staging
  application deployment has tenant isolation enabled.
- [ ] Set `SENTINEL_DNA_AUDIT_LOGGING_ENABLED=1` and verify the staging
  application deployment is emitting audit events.
- [ ] Confirm the evidence directory exists, is writable, and is under the
  approved append-only custody procedure.
- [ ] Confirm validation scripts are present and the evidence path is not
  shared with production.

## 6. Activation commands

From the repository root, run in order:

```powershell
.\deployment\staging\scripts\configure_trusted_browser_provider.ps1 -DryRun
node .\deployment\staging\scripts\verify_trusted_browser_provider.mjs
node .\deployment\staging\scripts\generate_trusted_browser_readiness_report.mjs
node .\deployment\staging\scripts\generate_trusted_browser_activation_troubleshooting_report.mjs
node .\deployment\staging\scripts\check_controlled_pilot_readiness.mjs
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1
```

Proceed only when the final command prints:

```text
READY_FOR_ANALYST_PILOT
```

The final command writes one non-secret report to:

`pilot-evidence/controlled-pilot-readiness-report-<timestamp>.json`

Any `BLOCKED_WITH_REASON` result or `TB_*` code stops activation. Do not
substitute the test adapter, bypass `browserAuth`, or retry through another
browser service.

For machine-readable integration, use:

```powershell
.\deployment\staging\scripts\check_controlled_pilot_activation.ps1 -Json -DryRun
```

The JSON output contains only `status` and safe diagnostic `codes`.

## 7. Readiness report format

The report is suitable for internal security review, SOC pilot approval, and
customer pilot documentation because it contains control statuses and safe
diagnostic categories only. It contains no customer data, credentials, paths,
tokens, cookies, or browser session material.

Required top-level fields:

```json
{
  "schema_version": "1.0",
  "generated_at_utc": "2026-09-01T00:00:00.000Z",
  "status": "READY_FOR_ANALYST_PILOT",
  "manifest_status": "PASS",
  "provider_status": "PASS",
  "image_digest_status": "PASS",
  "origin_status": "PASS",
  "tenant_isolation_status": "PASS",
  "audit_status": "PASS",
  "final_readiness_decision": "READY_FOR_ANALYST_PILOT",
  "checks": []
}
```

## 8. Human approval and evidence handoff

- [ ] Human security or SOC authority reviews the readiness artifact.
- [ ] Human authority confirms the external runtime, image, manifest, origin,
  tenant, audit, and evidence controls.
- [ ] Execute the pilot only after readiness passes and the human authority
  authorizes the controlled run.
- [ ] Validate the resulting evidence with the unchanged evidence validator.
- [ ] Archive the readiness report, evidence manifest, hashes, and revocation
  result under approved custody.
- [ ] Record `BLOCKED_WITH_REASON` if any authenticated gate is not measured;
  never infer readiness from endpoint health alone.
