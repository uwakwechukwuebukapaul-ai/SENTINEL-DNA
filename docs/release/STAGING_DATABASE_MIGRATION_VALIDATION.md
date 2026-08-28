# Staging Database Migration Validation

**Validation date:** 2026-08-28  
**Validation scope:** authoritative Sentinel DNA database migration lifecycle  
**Local validation host:** Windows development workspace  
**Target runtime:** Ubuntu staging with Docker Engine and PostgreSQL

This document records repository-side release validation. Docker Engine and a
disposable PostgreSQL target were not available in the validation workspace, so
runtime staging results remain an operator gate on `Sentinel-DNA-Staging`.

## Root cause

`database/migration_runner.py` registered only the normalized core migration.
The numbered migrations for canonical authority, identity bindings, provider
trust, billing, crypto intents, investigation memory, and organizational memory
were therefore not reachable through the production runner. Deployment Compose
also had no explicit one-shot migration step before application startup.

On a fresh PostgreSQL target this left `schema_migrations` and the canonical
authority tables absent. The application could then fail during startup while
opening its database session. A recurring `PostgreSQL connection failed`
message must still be treated as a separate URL, credential, or network issue;
missing schema is not itself a PostgreSQL connection error.

## Architecture change

- `database/migrations/registry.py` is the canonical registry for versions 1
  through 8 and rejects duplicate or non-contiguous versions.
- `MigrationRunner` applies the complete registry in ascending order, records
  successful versions in `schema_migrations`, and is idempotent.
- PostgreSQL migrations use the existing migration logic with backend-portable
  execution helpers. SQLite development and test behavior remains supported.
- Migration execution is transactional. SQLite explicitly begins a transaction
  only inside `MigrationRunner`, preserving existing repository transaction
  boundaries.
- Root, staging, and production Compose topologies expose a one-shot
  `migration` service running `python -m database.run_migrations`.
- The staging deployment script starts PostgreSQL and Redis, runs the migration
  job, and only then starts the application and edge service.
- WSGI import does not silently execute deployment migrations.

## Repository validation results

### Migration chain

Confirmed files exist:

```text
001_baseline.py
002_canonical_authority.py
003_identity_bindings.py
004_provider_tenant_trust.py
005_billing.py
006_crypto_intents.py
007_investigation_memory.py
008_organizational_cyber_memory.py
```

Registry output:

```text
registry: [(1, 'normalized_core_schema'), (2, 'Canonical tenants, identities, memberships, and authority metadata'), (3, 'Governed external provider subject to canonical actor bindings'), (4, 'Governed OIDC provider tenant trust'), (5, 'Commercial billing records'), (6, 'Durable provider-neutral crypto quotes and payment intents'), (7, 'Investigation memory learning records and append-only feedback audit'), (8, 'Tenant-scoped organizational cyber memory foundation')]
```

The SQLite runner test confirmed:

```text
first run:  (1, 2, 3, 4, 5, 6, 7, 8)
second run: ()
```

The deployment command is expected to print:

```text
database migrations applied: 1,2,3,4,5,6,7,8
database migrations applied: none
```

### Automated tests

```text
python -m pytest -q tests/database tests/staging tests/intelligence/ioc
59 passed, 2 skipped
```

```text
python -m pytest -q tests/identity
116 passed
```

```text
python -m pytest -q tests/audit
16 passed
```

The two PostgreSQL integration tests are opt-in and were skipped because
`SENTINEL_DNA_TEST_POSTGRES_URL` was not configured.

### Compose and deployment checks

All three Compose files parse successfully:

```text
compose_yaml: valid for docker-compose.yml, deployment/docker-compose.yml, deployment/staging/docker-compose.yml
```

The staging deployment script has the required order:

```text
staging_order: postgres -> redis -> migration -> app -> edge
```

Docker build, migration-container execution, container health, and PostgreSQL
schema queries could not be run locally because `docker` is not installed in
the validation workspace.

## Ubuntu staging validation commands

Run these commands on the Ubuntu staging host using the protected external
staging environment file. Do not place credentials in the repository or shell
history.

```bash
cd ~/SENTINEL-DNA
export STAGING_ENV_FILE=/etc/sentinel-dna/staging.env
export SENTINEL_DNA_BASE_URL=https://staging.example.internal
sh deployment/scripts/deploy.sh
```

Verify migration state:

```bash
docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file deployment/staging/docker-compose.yml \
  exec -T postgres psql -U sentinel -d sentinel_dna \
  -c "SELECT version FROM schema_migrations ORDER BY version;"
```

Verify required tables:

```bash
docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file deployment/staging/docker-compose.yml \
  exec -T postgres psql -U sentinel -d sentinel_dna \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('canonical_tenants','canonical_identities','canonical_memberships','canonical_identity_bindings','canonical_provider_tenant_trusts','billing_customers','crypto_payment_intents','investigation_memory','organizational_memory') ORDER BY table_name;"
```

Verify runtime health and idempotency:

```bash
docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file deployment/staging/docker-compose.yml ps

docker compose \
  --project-name sentinel-dna-staging \
  --env-file "$STAGING_ENV_FILE" \
  --file deployment/staging/docker-compose.yml run --rm migration
```

Expected state:

- `schema_migrations` contains versions 1 through 8.
- All nine required tables are present.
- The second migration run reports `database migrations applied: none`.
- PostgreSQL and Redis are healthy.
- The application is healthy and the staging edge is running.

## Security boundary validation

The authoritative 001-008 migration files contain no `DROP`, `TRUNCATE`,
destructive `DELETE`, user/role creation, default-user insertion, or admin
account creation. No credentials are embedded in the migration chain or the
Compose migration command. The migrations remain additive and preserve
tenant-scoped columns, canonical authority checks, append-only audit tables,
and append-only memory triggers.

Targeted identity and audit tests passed, including fail-closed provider
binding, tenant authorization, cross-tenant rejection, and audit redaction/
append-only behavior.

The legacy `database/migrations/migrate_ioc_contract.py` is an offline,
separate conversion utility and is not registered in the authoritative
deployment chain.

## Known limitations

1. Runtime execution against the actual Ubuntu staging PostgreSQL target is
   still required. Repository tests cannot substitute for Docker, PostgreSQL
   networking, or the real protected environment file.
2. PostgreSQL integration coverage remains opt-in and requires a disposable
   database URL.
3. The current checkout is dirty and reports branch
   `fix/auth-inactive-user-lookup`, not the handoff branch
   `remediation/postgresql-production-readiness`. Release custody must resolve
   this before generating the final immutable release evidence.
4. The controlled deployment test fixture cannot materialize one historical
   Git blob in this Windows workspace; Ubuntu release validation should run the
   controlled-deployment suite in a clean Git checkout.

## Remaining blockers before SOC analyst pilot

- Complete the Ubuntu staging runtime commands above and attach PostgreSQL
  query output, migration logs, `docker compose ps`, `/health`, and `/ready`
  evidence.
- Run the opt-in PostgreSQL integration tests against the disposable staging
  target, then repeat the migration job to prove idempotency.
- Reconcile the legacy SQLite-authoritative wording still present in the
  broader production runbook with the PostgreSQL deployment contract.
- Resolve release branch/worktree custody and create the immutable reviewed
  release commit.
- Complete existing pilot gates for protected secret custody, TLS/edge
  validation, backup/restore evidence, monitoring ownership, and independent
  release approval.

This validation does not authorize production promotion by itself.
