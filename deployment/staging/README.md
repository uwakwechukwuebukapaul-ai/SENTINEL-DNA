# Sentinel DNA Staging Preparation

This directory describes preparation for one isolated, non-production remote
analyst pilot. It is not a deployment authorization and contains no real
credentials, URLs, certificates, analyst identities, tenant identifiers, or
activation tokens.

## Important deployment boundary

Do not run `deployment/scripts/deploy.sh` as part of this preparation. The
script invokes `docker compose` without selecting a staging-specific Compose
file, and the repository root `docker-compose.yml` is a production contract.
Do not point either production Compose file at the existing ignored `.env`.

Use the [staging checklist](CHECKLIST.md) with an infrastructure operator who
can provide an approved private non-production runtime and remote boundary.
The [staging environment template](.env.example) is a non-secret template
only; inject values through the approved non-production secret/configuration
store and never commit the populated file.

## Required staging controls

The runtime must fail the preflight if any control is absent or if production
configuration, production credentials, or a production database is detected:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1
SENTINEL_DNA_SECURE_COOKIES=1
FLASK_DEBUG=0
```

Staging must use a separate database and non-production secret material. The
analyst-facing boundary is browser-only and private HTTPS, VPN, or
zero-trust; database, Redis, SSH, shell, repository, GitHub, and management
interfaces remain unavailable to the analyst.

## Health and rollback gates

After an approved operator starts the staging runtime, verify `/health` and
`/ready` through the private boundary, then verify authentication, pilot
authorization, tenant isolation, audit/provenance, monitoring, and the
emergency revocation path. These checks are not evidence of a real analyst
execution.

Rollback is limited to the isolated staging runtime and a verified staging
backup restored into a separate staging target. Never restore over a
production database and never include secrets or customer data in the backup.
