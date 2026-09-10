# Billing entitlement operational validation

`services/billing/validation/` is an evidence-only operational proof layer.
It exercises the existing billing repository, billing transition service,
entitlement resolver, canonical tenant/identity schema, and append-only audit
service against disposable SQLite fixtures. It does not redesign billing,
authentication, authorization, tenant enforcement, investigation orchestration,
verdict enforcement, or autonomous response.

## Scenarios

The runner executes five deterministic synthetic scenarios:

1. **Unpaid Tenant Lifecycle** proves an active tenant and identity can exist
   without a subscription while entitlement capabilities fail closed.
2. **Subscription Activation** applies the existing billing transition path
   from pending to active and proves that the new capability set comes only
   from the entitlement plan.
3. **Paid Tenant Downgrade** changes the synthetic subscription plan from
   Enterprise to Pro and proves restricted capabilities are removed while
   identity, tenant ownership, history, evidence, and provenance remain
   unchanged.
4. **Pre-Billing Investigation Preservation** retrieves a pre-existing
   investigation after activation and compares evidence/provenance digests.
5. **Billing Failure Handling** injects a synthetic amount mismatch. The
   existing transition transaction rejects it, leaves the subscription and
   entitlement unchanged, and records only a safe failure audit event.

Every scenario also checks tenant-bound audit records and attempts update and
delete operations against the existing audit append-only triggers. The attempts
are expected to fail and are performed only in disposable validation state.

## Evidence and replay

Reports contain synthetic tenant identifiers, before/after entitlement
transitions, bounded access decisions, audit validation, investigation and
provenance checks, and security invariants. They never contain credentials,
provider payloads, secrets, raw evidence, audit event UUIDs, or timestamps in
the replay input.

`replay_digest` hashes the canonical scenario evidence and is stable across
repeated runs. `report_digest` covers the rendered report and therefore changes
when `generated_at` changes. `write_immutable_report()` writes outside the
repository and refuses to replace an existing report or temporary file.

Run locally:

```powershell
python scripts/validate_billing_entitlements.py `
  --generated-at 2026-01-01T00:00:00+00:00 `
  --output C:\ProgramData\Sentinel-DNA\evidence\billing-entitlements.json
```

The command makes no payment-provider calls, performs no production billing
change, changes no credentials, performs no deployment, and invokes no
investigation runtime or autonomous action.

## Security boundary

Billing validation observes entitlement projections only. Authentication,
authorization, tenant isolation enforcement, verdict enforcement,
`InvestigationCoordinator`, `InvestigationOrchestrator`, `RuntimeTaskExecutor`,
and `InvestigationResult` remain outside the validation write boundary.
Advisory-only memory is not instantiated by the runner, and the report marks
that boundary as preserved.
