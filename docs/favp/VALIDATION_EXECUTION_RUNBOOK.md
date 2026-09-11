# FAVP Validation Execution Runbook

## Preflight

- Confirm the process is non-production and the FAVP feature flag is explicit.
- Confirm the existing trusted-browser activation gate remains unchanged and
  no FAVP route is mounted in production.
- Confirm scenario scope is synthetic or sanitized and no customer-sensitive
  data is being imported.
- Confirm an audit service is available. Mutations fail closed without it.

## Execution

- For the legacy FAVP operations catalog, use only its ten versioned
  scenarios. For the first execution-readiness cycle, use only the eight
  versioned `FAVP-EXE-*` scenarios in the execution catalog.
- Require an active participant and active access before assignment.
- Record start and completion timestamps, versions, the separate analyst
  decision, the advisory AI output, references, and limitations.
- Collect feedback after the result exists. Scores outside 1–5 are rejected.
- Do not interpret missing records as zero performance; reports label empty
  populations as `insufficient_data`.

## Revocation and closeout

Advance a participant to `REVOKED` when access must stop. The service changes
access status, records a timeline event, and emits an audit event in the same
transaction. Verify that revoked participants cannot receive assignments,
results, or feedback. Use `COMPLETED` and then
`DESIGN_PARTNER_CANDIDATE` only when the program owner has recorded the
corresponding decision.

## Incident response

Stop execution on any cross-tenant read, sensitive-data rejection, missing
audit event, provenance mismatch, unauthorized transition, or attempt to
invoke a security action. Preserve the existing evidence custody process and
trusted-browser activation state; do not bypass a gate to finish a validation.
