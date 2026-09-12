# FAVP Staging Launch Readiness

This procedure converts the engineered FAVP execution layer into one bounded
non-production validation environment. It does not enable production, import
customer data, provision credentials, or authorize a security action.

## Provision the disposable environment

Use only `deployment/staging/docker-compose.yml`. Confirm that PostgreSQL is
the authoritative `DATABASE_URL`, the target classification is
`disposable_staging`, the PostgreSQL health check is passing, and the
`staging_internal` network remains private. The FAVP evidence directory is the
separate named volume mounted at `/var/lib/sentinel/favp-evidence`.

Set these values through the approved staging configuration source:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_FAVP_OPERATIONS_ENABLED=1
SENTINEL_DNA_FAVP_SYNTHETIC_ONLY=1
SENTINEL_DNA_FAVP_PRODUCTION_ACCESS=0
SENTINEL_DNA_TENANT_ISOLATION_ENABLED=1
SENTINEL_DNA_AUDIT_LOGGING_ENABLED=1
SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION=external_non_production
SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION=disposable_staging
```

The Compose file defaults FAVP to disabled and hard-codes production access to
disabled. The command below only reads these values; it never changes them.

## Run the launch gate

From the repository root, run:

```powershell
py -3 deployment/staging/scripts/check_favp_launch_readiness.py --pretty
```

The command exits `0` only for `FAVP_STAGING_LAUNCH_READY`. It exits `1` for
any blocked check and emits only safe categories and bounded counts. It checks
the disposable PostgreSQL backend and schema, evidence custody, active
onboarded participants, all eight synthetic scenario packages, report
generation, audit append-only guards and history, tenant isolation, required
permissions, and the staging Compose contract.

## Operator sequence

1. Start or recreate only the staging PostgreSQL, migration, Redis, app, and
   private edge services.
2. Complete the reserved synthetic participant onboarding with explicit
   operator confirmation:

   ```powershell
   py -3 deployment/staging/scripts/onboard_favp_participant.py `
     --synthetic --operator-confirmation
   ```

   This creates no real identity or credential. It leaves the invitation,
   participant, and execution profile in `INVITED` with no access.
3. After the program owner explicitly confirms the bounded activation, run:

   ```powershell
   py -3 deployment/staging/scripts/activate_favp_participant.py `
     --synthetic --operator-confirmation
   ```

   The command records append-only audit events for invitation acceptance,
   NDA acceptance, terms acceptance, and participant activation in one
   transaction. It advances the participant to `ACTIVE_VALIDATION` and the
   execution profile to `ACTIVE` while production access remains `0`.
   If a prior attempt left reserved synthetic records behind, use the
   idempotent recovery command instead:

   ```powershell
   py -3 deployment/staging/scripts/recover_favp_staging.py `
     --synthetic --operator-confirmation
   ```
4. Run the launch-readiness command and resolve every blocked check. Verify an
   unexpired `ACTIVE` execution profile and the participant activation audit
   check.
5. Review the launch-readiness dashboard at
   `/api/favp/execution/launch-readiness` using the existing authenticated
   internal operator boundary.
5. Start only the eight versioned synthetic scenarios after human program-owner
   authorization.

Launch readiness is not evidence of analyst performance, revenue, customer
outcomes, certification, or design-partner conversion. Missing measurements
remain missing.
