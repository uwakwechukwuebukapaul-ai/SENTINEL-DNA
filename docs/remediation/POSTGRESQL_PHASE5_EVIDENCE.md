# PostgreSQL production readiness remediation — Phase 5 evidence

Generated: 2026-08-26

## Scope and custody

- Branch: `remediation/postgresql-production-readiness`
- Protected release commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- Phase 5 scope: portable core migration runner and bounded SQLite-to-backend conversion
- Source conversion scope: normalized core tables only
- Production database or customer data: not accessed

## Change evidence

| Objective | Evidence |
| --- | --- |
| Transactional migration runner | `database/migration_runner.py` applies ordered migrations through `DatabaseBackend.session()` and records idempotent versions in `schema_migrations`. |
| Backend coverage | The runner emits the normalized core DDL for either SQLite or PostgreSQL and uses the backend SQL boundary for parameters. |
| Fail-closed conversion | `database/migration_conversion.py` requires a read-only SQLite source, all normalized core tables, and required canonical columns before inserting anything. |
| Data preservation evidence | Conversion reports table names, row counts, and a content digest only; row contents are never serialized. |
| Repeatability | Re-running the migration runner produces no pending versions after version 1 is applied. |

## Validation

Focused Phase 5 validation: 29 passed, 1 skipped. The skipped test is the
opt-in PostgreSQL integration test because
`SENTINEL_DNA_TEST_POSTGRES_URL` was not configured. Conversion validation used
disposable SQLite source and target databases only. No network, credentials,
production database, or customer dataset was used.
