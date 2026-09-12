# FAVP Operations Guide

The FAVP Operations Platform is the internal execution layer for a bounded
30-day Founding Analyst Validation Program. It records operator-supplied
participant and organization metadata, synthetic scenario work, analyst
feedback, provenance references, and measured commercial signals.

## Boundary

The platform is opt-in and non-production only. Set
`SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1` only in an approved staging or local
environment. Production processes do not construct the service or register
its API. Existing trusted-browser activation and production deployment gates
are unchanged.

The platform never stores passwords, tokens, cookies, browser sessions, raw
customer evidence, or credential-bearing contact data. `contact_reference` is
an operator-controlled reference, not a credential or invitation secret.

## Program states

`INVITED`, `APPLIED`, `SCREENING`, `ACCEPTED`, `ONBOARDING`,
`ACTIVE_VALIDATION`, `COMPLETED`, `DESIGN_PARTNER_CANDIDATE`, `DECLINED`, and
`REVOKED` are recorded explicitly. Invalid transitions fail closed. A
participant must be in `ACTIVE_VALIDATION` with active access before a
scenario can be assigned or completed.

## Operator sequence

1. Confirm synthetic/sanitized data scope and program-owner authorization.
2. Create an organization record and a participant record from real,
   operator-supplied program information. The service does not seed examples.
3. Record the invitation. Invitation creation always leaves the participant
   and execution profile in `INVITED` with no access.
4. Require explicit operator confirmation, then run the staging-only
   activation workflow. It records immutable invitation-accepted,
   NDA-accepted, terms-accepted, and participant-activated audit events and
   advances the linked records to `ACTIVE_VALIDATION` / `ACTIVE`.
5. Assign catalog scenarios and capture the analyst decision separately from
   the AI recommendation.
6. Record structured feedback and provenance references.
7. Revoke access immediately when required; verify future writes fail closed.
8. Review the KPI snapshot and validation report with the program owner.

## API activation

The `/api/favp` blueprint is mounted only when the non-production feature flag
is enabled. It uses existing role and request-context authorization. Managers
administer program records; analysts can read and execute only their own
workspace. No route performs authentication, browser automation, provisioning,
or security action execution.

## Reserved synthetic staging activation

Create and activate the reserved fixture as two separate operator actions:

```powershell
python deployment/staging/scripts/onboard_favp_participant.py `
  --synthetic --operator-confirmation
python deployment/staging/scripts/activate_favp_participant.py `
  --synthetic --operator-confirmation
```

Activation fails closed unless staging, synthetic-only mode, tenant isolation,
audit logging, and `SENTINEL_DNA_FAVP_PRODUCTION_ACCESS=0` are confirmed.
Human program-owner authorization remains required and the production
`activation_performed` flag remains `false`; only disposable staging
execution access is granted.

If an interrupted staging attempt left reserved synthetic records behind, use
the idempotent recovery command. It reuses the reserved organization,
participant, invitation, and profile, creates only missing lifecycle records,
and safely replays completed activation without duplicating audit events:

```powershell
python deployment/staging/scripts/recover_favp_staging.py `
  --synthetic --operator-confirmation
```
