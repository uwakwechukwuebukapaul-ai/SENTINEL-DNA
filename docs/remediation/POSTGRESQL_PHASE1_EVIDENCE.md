# PostgreSQL production readiness remediation — Phase 1 evidence

Generated: 2026-08-26

## Scope and custody

- Branch: `remediation/postgresql-production-readiness`
- Release tag: `v1.0.0-rc1`
- Release commit at remediation start: `30c9568012879319675a4c86eeb712519f61dfe3`
- Release custody: preserved; remediation work is confined to the branch above
- Deployment activity: none
- Secrets: none added or recorded
- Phase boundary: backend foundation only; repository migration not performed

## Requirements evidence

| Requirement | Evidence |
| --- | --- |
| Backend abstraction boundary | `database/backend.py` defines `DatabaseBackend`, `DatabaseSettings`, `SQLiteBackend`, `PostgreSQLBackend`, and the backend factory. |
| PostgreSQL driver support | `requirements.txt` adds `psycopg[binary]` 3.x; the driver is loaded lazily by `PostgreSQLBackend`. |
| `DATABASE_URL` authority | `DatabaseSettings.from_environment()` selects PostgreSQL first and ignores the SQLite path for selection when a valid URL is present. |
| SQLite test compatibility | Explicit `DatabaseConnection(path)` remains SQLite-backed, including row factories, foreign keys, and busy timeout behavior. |
| Production fail-closed behavior | Production backend resolution requires a valid `postgres://` or `postgresql://` URL and raises a configuration error otherwise. |
| Direct SQLite inventory | 43 Python files contain direct `sqlite3` references; the categorized inventory is below. |
| Repository migration deferred | No repository files were converted to PostgreSQL SQL or removed from SQLite. |
| Architecture documentation | `docs/architecture/DATABASE_BACKEND_BOUNDARY.md`. |

## Direct `sqlite3` inventory

Inventory command: `rg -l --glob '*.py' --glob '!**/__pycache__/**' "import sqlite3|from sqlite3 import|sqlite3\\.connect|sqlite3\\.Connection|sqlite3\\.Row|sqlite3\\.Error" .`

### Active application and data access (26)

```text
analytics.py
check_db.py
check_ioc.py
check_tables.py
cleanup_cases.py
correlation_engine.py
dashboard/app.py
database.py
database/backend.py
database/canonical_authority.py
database/migrations/migrate_ioc_contract.py
find_case.py
migrate_database.py
services/auth/privileged_provisioning.py
services/auth/routes.py
services/billing/repository.py
services/billing/validation/runner.py
services/dashboard/dashboard_service.py
services/hunting/repository.py
services/intelligence/agent_memory/repository.py
services/intelligence/agent_orchestration/audit.py
services/intelligence/memory/organizational_repository.py
services/intelligence/memory/repository.py
services/intelligence/repository/provider_observation_repository.py
services/intelligence/threat_intelligence/repository.py
services/investigation_runtime/persistence/sqlite_investigation_repository.py
```

### Deployment and recovery validation (3)

```text
deployment/disaster_recovery/sqlite_backup.py
deployment/validation/database_rehearsal.py
deployment/validation/recovery.py
```

### Archived tools (4)

```text
archive/legacy/db-tools/add_evidence.py
archive/legacy/db-tools/compare_db.py
archive/legacy/db-tools/incident_viewer.py
archive/legacy/db-tools/update_case.py
```

### Tests (10)

```text
tests/dashboard/test_command_center.py
tests/dashboard/test_dashboard_app.py
tests/deployment/test_deployment_contract_validation.py
tests/deployment/test_sqlite_backup.py
tests/hunting/test_hunting.py
tests/identity/test_canonical_authority.py
tests/intelligence/ioc/test_ioc_contract_migration.py
tests/intelligence/ioc/test_ioc_repository_contract.py
tests/intelligence/memory/test_investigation_memory_learning.py
tests/intelligence/memory/test_organizational_cyber_memory.py
```

The inventory is intentionally complete for direct Python `sqlite3` imports,
connections, row/error types, and annotations. The new backend module is the
only new direct reference and centralizes the SQLite implementation.

## Validation record

Focused foundation/deployment validation: 35 passed.

Clean-worktree full suite: 2,987 passed, 6 skipped, 1 pre-existing
branch-contract failure. The failure is
`tests/deployment/test_release_hygiene_manifest.py::test_manifest_contains_state_identity_and_evidence_references`,
which asserts the branch is `main`; the requested remediation branch is
`remediation/postgresql-production-readiness`. No implementation test failed.

PostgreSQL connectivity is not exercised here: no production deployment,
external database, or credentials are authorized in Phase 1. The PostgreSQL
backend's driver and configuration paths are covered without opening a
network connection.
