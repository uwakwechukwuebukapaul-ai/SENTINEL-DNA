# PostgreSQL rehearsal package

## Scope

The isolated package at `rehearsal/postgresql/` is an operator-controlled,
non-deploying PostgreSQL 16 rehearsal lane. It uses an ephemeral Compose
`tmpfs`, a dedicated `SENTINEL_DNA_REHEARSAL_POSTGRES_URL`, and an explicit
approval guard. It never consumes production `DATABASE_URL` and never writes
evidence inside the repository.

## Implemented checks

- empty-target migration and migration idempotency;
- normalized schema inventory and generated identity behavior;
- representative synthetic case, note, and evidence CRUD;
- JSON/text memory fields and provenance preservation;
- tenant isolation across memory, organizational memory, and audit reads;
- append-only organizational-memory and audit tamper checks;
- transactional rollback and failed-migration rollback;
- deterministic replay and report digests without serialized rows or secrets.

The package records backup/restore as `not_executed`; a PostgreSQL rehearsal
report is not a production-readiness approval.

## SQLite inventory classification

| Remaining path | Classification | Disposition |
| --- | --- | --- |
| `database/backend.py` | acceptable compatibility layer | SQLite remains behind the explicit local/test backend. |
| `database/portability.py` | acceptable compatibility layer | SQLite introspection and integrity recognition are centralized. |
| `database/migrations/**`, `database/migration_conversion.py` | migration tooling | SQLite source migration/conversion only; not production persistence. |
| `deployment/validation/**`, `deployment/disaster_recovery/sqlite_backup.py` | recovery/rehearsal tooling | SQLite-only offline validation and legacy recovery paths. |
| `services/billing/validation/runner.py` | test fixture | Disposable synthetic billing validation state. |
| `analytics.py`, `correlation_engine.py` | legacy compatibility scripts | Standalone scripts not imported by the application container. |
| `check_*.py`, `cleanup_cases.py`, `find_case.py`, `database.py`, `migrate_database.py`, `archive/**` | development/archive tooling | Explicitly outside production runtime wiring. |

No prioritized production repository directly opens SQLite after the
portability remediation.

## Current execution status

The authorized disposable PostgreSQL rehearsal has completed successfully.
The external report is:
`C:\Temp\sentinel-dna-postgres-full-rehearsal.json`.

The report is bound to remediation HEAD
`94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`, records no production database
access or customer data, and includes migration, idempotency, schema, CRUD,
identity, tenant isolation, provenance, audit, transaction rollback, failed
migration rollback, and deterministic digest checks. Backup/restore remains
`not_executed`; PostgreSQL production readiness remains blocked.

## Lifecycle rule

The standalone migration report and the full rehearsal require separate
disposable PostgreSQL lifecycles. `run_migration.py` intentionally leaves a
migrated target populated; `run_rehearsal.py` intentionally rejects a
non-empty target before running its own migration and rollback checks. The
operator must use separate Compose project names and host ports, or tear down
the first disposable target before starting the second. The runners never
automatically reset or destroy a target.
