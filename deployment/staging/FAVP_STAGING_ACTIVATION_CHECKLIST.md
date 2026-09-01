# FAVP Staging Environment Activation Checklist

This is an operator-controlled checklist for Phase 1. It is not an approval,
does not provision identities, and must be completed only against the isolated
non-production Compose environment.

## Environment readiness

- [ ] `SENTINEL_DNA_ENV=staging` is confirmed.
- [ ] `SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1` is set in staging only.
- [ ] `SENTINEL_DNA_FAVP_SYNTHETIC_ONLY=1` is confirmed.
- [ ] `SENTINEL_DNA_FAVP_PRODUCTION_ACCESS=0` is confirmed.
- [ ] Configuration source is classified `external_non_production`.
- [ ] Database target is classified `disposable_staging`.
- [ ] PostgreSQL is a dedicated staging target and passes its health check.
- [ ] Redis, volumes, and private `staging_internal` networking are isolated.
- [ ] Dedicated `/var/lib/sentinel/favp-evidence` custody volume is mounted and writable.

Initialize the disposable state from the migration service before running the
launch gate:

```sh
python deployment/staging/scripts/initialize_favp_staging.py
python deployment/staging/scripts/check_favp_launch_readiness.py --pretty
```

The initializer applies staging migration 9, verifies the audit guards, and
writes only the non-secret `.favp-storage-manifest.json` marker in the named
evidence volume. It does not create participant or organization records.

## Security approval

- [ ] Program owner approved the bounded FAVP scope.
- [ ] Security owner approved the staging target and rollback owner.
- [ ] Existing trusted-browser and pilot activation gates are unchanged.
- [ ] No production endpoint, database, credentials, or customer data is in scope.
- [ ] Audit table and append-only guards are present.
- [ ] Tenant-scoped tables and permission checks are verified.
- [ ] Launch command output is `FAVP_STAGING_LAUNCH_READY`.

## Participant onboarding readiness

- [ ] Organization and analyst records were supplied by the operator, not seeded.
- [ ] Invitation, NDA, terms, and onboarding statuses are recorded.
- [ ] At least one participant is `ACTIVE` with an unexpired access window.
- [ ] Access revocation owner and expiry review time are recorded.
- [ ] No credentials, tokens, cookies, or browser sessions are stored.

For a disposable synthetic readiness run, use the explicitly authorized
reserved fixture mode:

```sh
python deployment/staging/scripts/onboard_favp_participant.py \
  --synthetic --operator-confirmation
```

This creates exactly one reserved synthetic participant and invitation. It
leaves both records in `INVITED`, with NDA/terms/onboarding `NOT_STARTED` and
access not granted. It stores no credentials and refuses non-staging or
non-synthetic configuration.

After the human program owner confirms activation, run the separate command:

```sh
python deployment/staging/scripts/activate_favp_participant.py \
  --synthetic --operator-confirmation
```

This records append-only audit events for invitation acceptance, NDA
acceptance, terms acceptance, and participant activation in one transaction.
It ends with an unexpired `ACTIVE` execution profile and `ACTIVE_VALIDATION`
program participant. Production access remains `0`, synthetic-only mode
remains enabled, and the launch gate's `activation_performed` value remains
`false`.

If a prior interrupted run left the reserved organization, participant,
invitation, or profile behind, use the idempotent recovery command instead of
re-running ad-hoc inserts:

```sh
python deployment/staging/scripts/recover_favp_staging.py \
  --synthetic --operator-confirmation
```

Recovery reuses existing reserved records, creates only missing lifecycle
records through the audited onboarding path, and safely replays a completed
activation without duplicating required audit events. It remains restricted
to the reserved staging tenant.

For a real participant, use the same command only after the program owner
supplies all required participant and organization references. Without
`--synthetic`, the command records an invitation and leaves the execution
profile in `INVITED`; the operator must separately verify NDA, terms, and
onboarding before advancing the profile.

## Scenario package verification

- [ ] All eight `FAVP-EXE-*` scenarios are present and version matched.
- [ ] Each package is synthetic/sanitized and contains references only.
- [ ] MITRE mappings, objectives, criteria, decision checkpoints, and AI boundary tests are present.
- [ ] Analyst decisions remain separate from advisory AI recommendations.

## First-run and rollback

- [ ] Use `simulation/favp-first-run-package.json` only as a test planning artifact.
- [ ] Generate a unique operator run identifier; do not reuse fixture evidence.
- [ ] Capture evidence references, provenance references, versions, and hashes only.
- [ ] Stop immediately on tenant mismatch, audit failure, provenance failure, or boundary violation.
- [ ] Rollback means stop the staging cycle, revoke participant access, and preserve audit/evidence references.
- [ ] Do not restore over production or delete evidence before the retention decision.

## Access revocation procedure

1. Transition the execution profile to `REVOKED` through the authorized operator
   route.
2. Confirm new sessions and writes fail closed for that profile.
3. Verify the revocation audit event and timestamp.
4. Notify the program owner and preserve the non-secret evidence references.

Phase 1 is complete only after the readiness command passes, the human
security/program approvals are recorded, and the end-to-end synthetic cycle is
executed in disposable staging. This checklist itself is not evidence of any
such execution.
