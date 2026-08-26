# PostgreSQL operational evidence gate matrix

Status snapshot for remediation HEAD
`94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`. This matrix is not a release
approval.

| Gate | Status | Evidence or blocker |
| --- | --- | --- |
| Disposable PostgreSQL migration/full rehearsal | PASS | External report at `C:\Temp\sentinel-dna-postgres-full-rehearsal.json`; report digest `4b97cc9338eb833330572036906447b85f2c3da37da9960f13b850458c979ca9` |
| Migration ordering/idempotency/schema/CRUD | PASS | Covered by the external rehearsal report |
| Tenant isolation/provenance/audit integrity | PASS | Covered by the external rehearsal report |
| Transaction rollback/failed migration rollback | PASS | Covered by the external rehearsal report |
| Production-like backup/restore | PASS (bounded rehearsal scope) | `pg_dump`/`pg_restore` successful; dump `C:\Temp\sentinel-dna-rehearsal.dump`; SHA-256 `BC6932E9194F38526EC75982F681D253C0764B951A9A8B4D4CA3B5C3FB1FE4D4`; restore target `sentinel_restore_test`; `schema_migrations` count `1` |
| Credential rotation/revocation | PASS (bounded rehearsal scope) | `ALTER USER` successful; old password rejected; rotated credential accepted |
| Monitoring and ownership | BLOCKED | Operational owners, alert routing, and attestations explicitly unknown |
| Stale evidence reconciliation | PASS | Outdated blocked-state references reconciled; remaining blockers are intentional |
| Remediation custody | BLOCKED | Worktree remains dirty; final writable Git custody/independent review outstanding |

Production readiness remains blocked until every partial or blocked gate has
independent external evidence and custody review.
