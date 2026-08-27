# Sentinel DNA Staging Preparation

This directory describes preparation for one isolated, non-production remote
analyst pilot. It is not a deployment authorization and contains no real
credentials, URLs, certificates, analyst identities, tenant identifiers, or
activation tokens.

## Runtime contract

The staging runtime is defined by
`deployment/staging/docker-compose.yml` and uses the canonical
`wsgi:application` entrypoint. The application, PostgreSQL, and Redis services
are private; only the staging edge is exposed, and that edge must be private
HTTPS, VPN, or zero-trust infrastructure.

`deployment/scripts/deploy.sh` is staging-only. It requires an absolute
`STAGING_ENV_FILE` outside the repository and explicitly selects the staging
Compose file. It must not be run as part of this repository gate. The root
`docker-compose.yml` and `deployment/docker-compose.yml` remain production
contracts and must not be used for staging.

Use the [staging checklist](CHECKLIST.md) with an infrastructure operator who
can provide an approved private non-production runtime and remote boundary.
The [staging environment template](.env.example) is a non-secret template
only; inject values through the approved non-production secret/configuration
store and never commit the populated file or use the repository `.env`.

## Required staging controls

The runtime must fail the preflight if any control is absent or if production
configuration, production credentials, or a production database is detected:

```text
SENTINEL_DNA_ENV=staging
SENTINEL_DNA_PILOT_ACCESS_REQUIRED=1
SENTINEL_DNA_SECURE_COOKIES=1
FLASK_DEBUG=0
```

The runtime also requires `SENTINEL_DNA_CONFIG_SOURCE_CLASSIFICATION` to be
`external_non_production` and
`SENTINEL_DNA_DATABASE_TARGET_CLASSIFICATION` to be
`disposable_staging`. These values are defense-in-depth declarations; network,
database-role, target-ownership, and secret-store isolation remain
infrastructure responsibilities. No hostname heuristic is used.

Staging must use separate database, Redis, volumes, and non-production secret
material. The analyst-facing boundary is browser-only and private; database,
Redis, SSH, shell, repository, GitHub, and management interfaces remain
unavailable to the analyst.

## Health and rollback gates

After an approved operator starts the staging runtime, verify `/health` and
`/ready` through the private boundary, then verify authentication, pilot
authorization, tenant isolation, audit/provenance, monitoring, and the
emergency revocation path. These checks are not evidence of a real analyst
execution.

Rollback is limited to the isolated staging runtime and a verified staging
backup restored into a separate staging target. Never restore over a
production database and never include secrets or customer data in the backup.
