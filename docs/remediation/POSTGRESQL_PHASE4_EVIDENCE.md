# PostgreSQL production readiness remediation — Phase 4 evidence

Generated: 2026-08-26

## Scope and custody

- Branch: `remediation/postgresql-production-readiness`
- Protected release commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- RC1, main, release artifacts, and RC1 evidence were not modified.
- No deployment or live PostgreSQL connection was performed.
- Work remains uncommitted pending final validation.

## Repository portability completed

The following production persistence paths now receive a `DatabaseBackend` or
use the process-level backend boundary. Explicit SQLite paths remain supported
for local development and tests.

- investigation state persistence;
- investigation and organizational memory, including tenant predicates,
  provenance, audit hashes, and append-only enforcement;
- threat intelligence indicators and case links;
- billing transactions, subscriptions, checkout, crypto, and event
  persistence;
- canonical audit events and agent orchestration audit;
- canonical tenant/identity schema setup;
- authentication schema introspection, identity insertion, and privileged
  provisioning error classification;
- dashboard and hunting persistence;
- agent memory persistence;
- investigation lifecycle, execution, and provider-observation schema
  introspection.

Portability helpers centralize placeholder-compatible SQL execution, table
column discovery, integrity-error classification, generated identity syntax,
and append-only trigger differences. PostgreSQL uses `information_schema`,
`RETURNING`, `ON CONFLICT`, identity columns, and PostgreSQL trigger functions;
SQLite retains its local row factory, PRAGMA configuration, and test behavior
inside the backend implementation.

## Remaining direct SQLite inventory and classification

| Path or family | Classification | Disposition |
| --- | --- | --- |
| `database/backend.py` | compatibility adapter / SQLite backend | Allowed. This is the intentional SQLite implementation behind the boundary. |
| `database/migrations/**`, `database/migration_conversion.py` | migration utility | Allowed exception. Source conversion is explicitly read-only SQLite tooling. |
| `deployment/validation/**`, `deployment/disaster_recovery/sqlite_backup.py` | rehearsal/recovery utility | Allowed exception. These validate or back up SQLite development state and are not production persistence repositories. |
| `analytics.py`, `correlation_engine.py` | legacy/development scripts | Not imported by the application container or dashboard runtime; retained as standalone SQLite compatibility scripts. |
| `migrate_database.py`, `check_*.py`, `cleanup_cases.py`, `find_case.py`, `database.py` | development/legacy tooling | Explicitly outside the production service wiring; retained for local SQLite maintenance and inspection. |
| `services/billing/validation/runner.py` | test/evidence fixture | Allowed exception. It creates disposable synthetic SQLite state for offline billing evidence. |
| `tests/**`, archived tools, and development scripts | test/development/archive | Allowed and outside production runtime. |

The production runtime inventory has no remaining direct `sqlite3.connect`,
`executescript`, `PRAGMA table_info`, `INSERT OR REPLACE/IGNORE`, or
`lastrowid` use outside those classified exceptions. Backend-specific SQLite
operations are now confined to `database/backend.py` and the centralized
portability helper.

## Validation

- Focused high-risk portability and backend tests: **50 passed**.
- Affected repository/application suite: **950 passed, 4 skipped**.
- Additional identity regression after schema transaction-boundary correction:
  **15 passed**.
- Database/billing/audit/auth regression slice: **75 passed**.
- `python -m compileall -q database dashboard services`: passed.
- `git diff --check`: passed.
- Live PostgreSQL integration test: skipped because
  `SENTINEL_DNA_TEST_POSTGRES_URL` is not configured.

The full external-temp regression remains the final validation step for this
slice. No result is treated as release evidence until it runs from a clean
external workspace.

## PostgreSQL rehearsal blockers

- No authorized disposable PostgreSQL instance or `SENTINEL_DNA_TEST_POSTGRES_URL`
  is available, so PostgreSQL execution, locking, extensions, and migration
  behavior remain unverified.
- Phase 5 migration/data conversion must be run against a real PostgreSQL
  target during rehearsal.
- Phase 6 deployment integration and Phase 7 rehearsal evidence require
  environment-specific secrets, network access, rollback/restore artifacts,
  and operator approval.
- The branch-contract test that expects `main` is intentionally incompatible
  with this remediation branch and is not an implementation failure.

This artifact records portability work and blockers; it does not claim
PostgreSQL production readiness.
