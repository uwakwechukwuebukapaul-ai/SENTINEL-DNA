# PostgreSQL production readiness remediation — Phase 2 evidence

Generated: 2026-08-26

## Scope and custody

- Branch: `remediation/postgresql-production-readiness`
- Release tag: `v1.0.0-rc1`
- Protected release commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- Phase 2 scope: runtime enablement behind the Phase 1 backend boundary
- Repository migration: not performed
- Production deployment: not performed
- Secrets: none added, loaded, or recorded

## Change evidence

| Objective | Evidence |
| --- | --- |
| PostgreSQL runtime enablement | `PostgreSQLBackend` now supports bounded connection configuration and is selected by the existing factory when `DATABASE_URL` is authoritative. |
| Dependency handling | `requirements.txt` declares `psycopg[binary]>=3.2,<4`; imports remain lazy and missing-driver errors are safe. |
| Connection lifecycle | PostgreSQL sessions use `autocommit=False`, commit successful work, rollback failed work, and always close connections. |
| Health validation | `DatabaseBackend.health_check()` is implemented by SQLite and PostgreSQL; `/health` and `/ready` use it. |
| Isolated integration tests | `tests/database/test_postgresql_integration.py` is opt-in via `SENTINEL_DNA_TEST_POSTGRES_URL` and uses `ON COMMIT DROP` temporary tables. |
| Repository boundary | No repository SQL, schema, or repository implementation was migrated. |

## Validation

Focused Phase 2 validation after the compatibility correction: 13 passed.
The opt-in PostgreSQL integration test remains skipped because
`SENTINEL_DNA_TEST_POSTGRES_URL` was not configured. No network or production
database access occurred.

Clean external checkout full regression: 2,992 passed, 7 skipped, 1 known
branch-contract failure. The failure is
`tests/deployment/test_release_hygiene_manifest.py::test_manifest_contains_state_identity_and_evidence_references`,
which asserts the branch is `main` while this remediation is intentionally on
`remediation/postgresql-production-readiness`. No implementation test failed.

The clean validation checkout included the Phase 2 compatibility correction as
commit `a8fdfd0` (`fix: preserve explicit sqlite compatibility boundary`). The
shared checkout's `.git` metadata is read-only in this environment, so the
same source and test changes remain present as the current working-tree delta
until normal repository commit access is available.

The full regression result and final remediation commit SHA are recorded after
the clean-worktree regression run.
