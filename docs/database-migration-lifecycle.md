# Sentinel DNA database migration lifecycle

## Scope

The files under `database/migrations/` are the authoritative, ordered schema
chain for the application persistence boundary. The registry in
`database/migrations/registry.py` discovers versions 1 through 8 and rejects
duplicate or non-contiguous version numbers before execution.

The chain is additive and idempotent. It does not create users, tenants,
memberships, credentials, or other operational data. Tenant and actor records
are created only through their governed application services.

## Execution flow

1. The deployment contract validates the protected environment and image.
2. PostgreSQL is started and must become healthy.
3. The one-shot `migration` service runs
   `python -m database.run_migrations` from the exact deployment image.
4. `MigrationRunner` opens one backend transaction, creates
   `schema_migrations`, applies each pending migration in ascending order, and
   records its version only after the migration succeeds.
5. A failed migration rolls back the transaction and prevents the application
   service from being promoted.
6. Only after the migration command succeeds is the application started or
   recreated.
7. `/health` and `/ready` are checked before traffic is enabled.

The application does not silently run the migration chain during WSGI import.
This keeps schema mutation visible in deployment output and makes the image,
environment, database target, and migration result auditable together.

## Deployment responsibilities

The operator supplies a protected environment file and a disposable staging or
approved production PostgreSQL target. The operator must run the migration
step with the same Compose file and image that will run the application.

Staging uses `deployment/scripts/deploy.sh`, which starts PostgreSQL, runs the
one-shot migration service, and then starts the app and private edge. If the
repository-root Compose file is used for the Ubuntu staging check, use the
same explicit sequence with service `migration` before `sentinel-dna`; do not
start the app first. The controlled production adapter runs the same migration
service explicitly before recreating the app and pins both services to the
verified image digest.

Do not use `docker compose down -v` as a migration procedure. Named volumes
are data-bearing state and require an approved backup and recovery decision.

## Rollback philosophy

Migrations are forward-only and destructive migrations are not permitted in
this chain. A migration failure is handled by transaction rollback, followed
by diagnosis and correction before retrying.

After a migration has committed, rollback means restoring a validated backup
to a separate target or applying a reviewed forward migration. Never erase or
rewrite production tables to simulate rollback, and never restore over the
source database without an approved recovery procedure.

## Staging promotion process

For each staging run:

1. Confirm the reviewed commit, image digest, non-production environment
   classification, and disposable database target.
2. Run the staging migration service and record its output.
3. Verify versions `1` through `8` in `schema_migrations`.
4. Verify canonical authority, provider trust, billing, crypto, investigation
   memory, and organizational memory tables.
5. Verify `/health`, `/ready`, authentication, tenant isolation, audit writes,
   and the private edge boundary.
6. Run the migration service a second time and confirm that no versions are
   pending.
7. Promote only with the migration evidence, backup/recovery evidence, and
   staging security checklist complete.

The staging database must not be pointed at production, and staging secrets
must not be reused for production.
