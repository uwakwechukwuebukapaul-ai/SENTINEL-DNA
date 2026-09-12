# Gate 4 Analyst Pilot Runbook

This runbook governs the controlled, non-production analyst pilot after the
Gate 4 infrastructure readiness decision. It does not authorize production
release, public exposure, unrestricted account creation, or use of real
customer data.

## Entry criteria and hard stops

Proceed only when the current readiness command returns exactly
`READY_FOR_ANALYST_PILOT` and every check is `PASS`. Stop for any failed,
missing, stale, or `NOT_MEASURED` prerequisite. Do not substitute a fixture,
mock, fake runtime, alternate origin, direct credential client, or bypass flag.

## Before pilot

Record each item as `PASS`, `FAIL`, `NOT_MEASURED`, or `BLOCKED` with a
non-secret observation reference.

- [ ] Confirm branch and reviewed source commit.
- [ ] Run `node deployment/staging/scripts/check_controlled_pilot_readiness.mjs`.
- [ ] Confirm the exact origin is
      `https://sentinel-dna-staging:18443` and certificate validation is
      enabled.
- [ ] Confirm Docker Compose project identity and record `docker compose ps`.
- [ ] Confirm only `127.0.0.1:18443->443/tcp` is published; stop for wildcard,
      LAN, public, management, or additional listeners.
- [ ] Confirm application, PostgreSQL, and Redis are healthy and their service
      ports are not published to the host.
- [ ] Confirm `/health` and `/ready` return HTTP 200 through the private edge.
- [ ] Confirm reviewed image, runtime, dependency lockfile, bridge, and
      external activation manifest digests are reconciled.
- [ ] Confirm current staging backup exists, its custody reference is recorded,
      and recovery ownership is known. Do not copy backup contents into Git.
- [ ] Confirm the pilot tenant is synthetic, isolated, and approved for this
      run; record only its non-secret identifier.
- [ ] Confirm exactly one analyst account is approved, role-bound to the
      synthetic tenant, and bounded by an explicit expiry.
- [ ] Confirm manager approval and the protected browser-auth channel are
      available. Never place credentials, tokens, cookies, or sessions in the
      runner or evidence.
- [ ] Confirm audit and provenance sinks are available in the deployed staging
      service and have an operator-owned observation reference.
- [ ] Confirm the analyst URL, if later approved, will remain private and
      origin-scoped. Do not issue it during preparation.

## During pilot

1. Start a unique, non-secret operator run ID and record the UTC start time.
2. The manager opens the login page through the certified origin and completes
   authentication only through the approved browser-auth handoff.
3. Confirm the manager role and tenant context through the application’s
   server-derived identity response. Record no credential or session value.
4. Verify that a manager write without CSRF is denied and causes no state
   change; then use the valid protected workflow.
5. With explicit human approval, provision only the approved synthetic tenant
   and one synthetic analyst identity, if provisioning is in scope for this
   run. Otherwise record provisioning as `NOT_PERFORMED`.
6. Have the analyst activate and sign in through the protected channel. Confirm
   analyst role, tenant, authorization expiry, and secure-cookie behavior.
7. Run one approved synthetic investigation through the canonical workflow.
   Confirm tenant-scoped audit and provenance references.
8. Review the analyst workspace and investigation result. Confirm all returned
   objects are scoped to the assigned synthetic tenant.
9. Request a known foreign-tenant synthetic resource and require the documented
   denial (`403` or indistinguishable `404`).
10. Exercise the approved denial matrix for admin escalation, pilot
    provisioning, database, shell/container, destructive, and runtime-control
    surfaces. Record exact non-secret HTTP observations.
11. Confirm AI output is advisory-only and explicitly requires human review.
    No AI output may approve or execute an action.
12. Collect analyst feedback without recording credentials, tokens, cookies,
    session material, or customer data.
13. On any anomaly, stop immediately and follow the rollback procedure.

The pilot evidence must mark every unperformed or unmeasured gate explicitly;
it must never infer `PASS` from source inspection, endpoint health, or an HTTP
status alone.

## After pilot

- [ ] Revoke the pilot authorization with a reason.
- [ ] Deactivate the synthetic analyst account and invalidate active sessions.
- [ ] Verify post-revocation denial for login renewal, workspace reads,
      investigation reads, and feedback/action writes.
- [ ] Confirm revocation and denial events are tenant-scoped, auditable, and
      secret-free.
- [ ] Create one unique append-only evidence record in approved custody.
- [ ] Run `node deployment/staging/scripts/validate_manual_analyst_pilot_evidence.mjs`
      against the evidence record.
- [ ] Collect pilot metrics: workflow completion, latency, denial outcomes,
      audit/provenance coverage, operator interventions, and analyst feedback.
- [ ] Triage issues by severity, security impact, reproducibility, and owner.
- [ ] Record unresolved items as blockers or follow-up work; do not convert
      `NOT_MEASURED` or `FAIL` into `PASS`.
- [ ] Release decision: continue pilot, remediate and repeat, or stop and
      rollback. Production release requires a separate production gate and
      approval.

## Rollback and incident handling

On failed controls, unexpected access, credential-handling concerns, runtime
failure, evidence contamination, or unauthorized exposure:

1. Stop the pilot and preserve the non-secret run ID and UTC time.
2. Keep Gate 4 blocked and notify release/security ownership.
3. Revoke authorization, deactivate the analyst, and invalidate sessions.
4. Verify post-revocation denial and preserve only safe audit/evidence hashes.
5. Tear down the external runtime using its approved lifecycle/revocation
   procedure.
6. Repair or rotate only through the approved custody and deployment workflow.
7. Re-run all readiness and authenticated gates before any restart.

## References

- [`gate4-controlled-analyst-pilot-handoff.md`](../../docs/gate4-controlled-analyst-pilot-handoff.md)
- [`CONTROLLED_ANALYST_PILOT_EXECUTION_CHECKLIST.md`](./CONTROLLED_ANALYST_PILOT_EXECUTION_CHECKLIST.md)
- [`CONTROLLED_ANALYST_PILOT_ACTIVATION_CHECKLIST.md`](./CONTROLLED_ANALYST_PILOT_ACTIVATION_CHECKLIST.md)
- [`GATE4_OPERATOR_RUNBOOK.md`](./GATE4_OPERATOR_RUNBOOK.md)
