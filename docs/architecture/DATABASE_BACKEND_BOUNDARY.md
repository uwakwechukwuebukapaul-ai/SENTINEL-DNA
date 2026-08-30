# Database backend boundary — Phase 1

Status: foundation only. This document describes the PostgreSQL readiness
boundary introduced on `remediation/postgresql-production-readiness`.

## Contract

Application services and repositories depend on the small database backend
contract exposed by `database.backend.DatabaseBackend`:

- `connect()` returns the native connection for the selected backend.
- `session()` owns commit, rollback, and close behavior.
- `health_check()` runs a bounded backend-native `SELECT 1` probe and returns
  only a boolean health result.
- `backend_name` identifies `sqlite` or `postgresql` without exposing backend
  selection logic to callers.

`database.connection` remains a compatibility facade for existing imports.
Explicit `DatabaseConnection(path)` construction remains SQLite-compatible for
tests and existing repository call sites. New wiring should use
`create_database_backend()` or `database_for_environment()`.

## Configuration precedence

`DATABASE_URL` is authoritative whenever it is non-empty:

1. A `postgres://` or `postgresql://` URL selects `PostgreSQLBackend`.
2. `SENTINEL_DNA_DB_PATH` is ignored for backend selection when that URL is
   configured.
3. When no URL is configured, non-production environments fall back to the
   SQLite path (defaulting to `soc.db`) for local testing.
4. Production backend resolution fails closed without a valid PostgreSQL URL.

The PostgreSQL driver is `psycopg` 3 (`psycopg[binary]` in
`requirements.txt`). It is imported lazily, so SQLite-only test runs do not
need a live PostgreSQL server. Connection errors never include the URL, which
may contain credentials.

PostgreSQL connections use explicit non-autocommit transactions, a bounded
connection timeout, and `session()` cleanup that rolls back failed work and
always closes the connection. Health probes use the same lifecycle and do not
expose driver exceptions through the health API. Application `/health` and
`/ready` routes call `database.health_check()` through this boundary.

## Phase boundary

Phase 1 does not migrate repositories, SQL placeholders, schema definitions,
or SQLite-specific operational tools. The direct `sqlite3` inventory is
recorded in the Phase 1 evidence report. Repository migration is a follow-on
phase and must introduce backend-neutral SQL/contracts incrementally with
SQLite regression coverage.

```text
environment
    |
    v
DatabaseSettings.from_environment()
    |
    +--> PostgreSQLBackend (production DATABASE_URL)
    |
    +--> SQLiteBackend (local/test path)
    |
    v
DatabaseBackend contract
    |
    v
repositories/services  [not migrated in Phase 1]
```

## Integration-test boundary

`tests/database/test_postgresql_integration.py` is marked `postgresql` and
requires the explicitly supplied `SENTINEL_DNA_TEST_POSTGRES_URL`. It never
uses `DATABASE_URL`, production secrets, or a production database. Each test
uses a PostgreSQL temporary table with `ON COMMIT DROP`; absent the dedicated
test URL, it skips rather than contacting a network service. Unit tests cover
the driver-missing path and lifecycle semantics with an in-memory fake driver.
