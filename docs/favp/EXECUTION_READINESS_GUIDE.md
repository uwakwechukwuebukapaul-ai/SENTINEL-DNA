# FAVP Execution Readiness Guide

This guide prepares one bounded, non-production analyst validation cycle. It
does not activate the trusted browser, provision accounts, issue credentials,
or authorize production access.

## Activation contract

The operator must explicitly set all of the following in the approved
non-production environment:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1
SENTINEL_DNA_FAVP_SYNTHETIC_ONLY=1
SENTINEL_DNA_FAVP_PRODUCTION_ACCESS=0
SENTINEL_DNA_TENANT_ISOLATION_ENABLED=1
SENTINEL_DNA_AUDIT_LOGGING_ENABLED=1
SENTINEL_DNA_FAVP_EVIDENCE_DIR=<approved writable custody directory>
```

The readiness result is `READY_FOR_FAVP_EXECUTION` only when the database,
evidence directory, existing pilot permissions, audit service, tenant
isolation, synthetic-only mode, and non-production boundary all pass. The
activation-check endpoint is read-only; it does not set the feature flag.

## Participant gate

An execution profile links to an operator-created participant record. The
platform never fabricates an analyst or organization. The profile state machine
is `INVITED → APPLIED → APPROVED → ONBOARDED → ACTIVE`, with `SUSPENDED`,
`COMPLETED`, and `REVOKED` as controlled outcomes. `ONBOARDED` requires
recorded NDA and terms acceptance; `ACTIVE` requires completed onboarding and
a future access expiry.

## Cycle gate

Use only the eight versioned synthetic execution scenarios. Start a session
only for an active, unexpired profile. Submit the analyst decision separately
from the AI recommendation. Validate evidence references after the session is
complete. Any `FAIL`, `NOT_MEASURED`, missing audit event, expired access,
tenant mismatch, or advisory-boundary violation stops the cycle.

## Closeout

Review the individual report, organization summary, progress dashboard, and
unfilled final report template. Report observed evidence, analyst feedback,
system measurements, limitations, and future improvements separately. Never
turn insufficient data into a success metric, certification, customer result,
or revenue claim.
