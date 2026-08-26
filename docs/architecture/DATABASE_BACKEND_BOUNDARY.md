# Database backend boundary — Phase 1

Status: foundation only. This document describes the PostgreSQL readiness
boundary introduced on `remediation/postgresql-production-readiness`.

## Contract

Application services and repositories depend on the small database backend
contract exposed by `database.backend.DatabaseBackend`:

- `connect()` returns the native connection for the selected backend.
- `session()` owns commit, rollback, and close behavior.
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

