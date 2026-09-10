# PostgreSQL production readiness remediation - Phase 7 evidence

## Scope and custody

- Rehearsal type: authorized disposable PostgreSQL 16 rehearsal
- Evidence artifact: `C:\Temp\sentinel-dna-postgres-full-rehearsal.json`
- Branch: `remediation/postgresql-production-readiness`
- Evidence HEAD: `94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`
- Protected release commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- Production deployment: not performed
- Production database touched: `false`
- Customer data used: `false`
- Secrets serialized: `false`

The evidence records `worktree_dirty: true`; this remains a custody
reconciliation item before release approval.

## Completed disposable rehearsal checks

- migration from empty target: passed;
- migration ordering: passed, first run applied version `1`;
- migration idempotency: passed, second run applied no versions;
- schema compatibility and inventory: passed;
- generated identity behavior: passed;
- representative repository CRUD: passed;
- tenant isolation: passed for synthetic `tenant-a` and `tenant-b` records;
- provenance preservation: passed;
- audit integrity and append-only tamper checks: passed;
- transaction rollback: passed;
- failed migration rollback: passed;
- deterministic replay and report digests: independently validated;
- backup/restore: manual dump/restore success reported with external dump
  checksum `BC6932E9194F38526EC75982F681D253C0764B951A9A8B4D4CA3B5C3FB1FE4D4`;
  restore target `sentinel_restore_test` reported `schema_migrations` count `1`;
- credential rotation/revocation: manual `ALTER USER` success reported, old
  password rejected, and rotated credential accepted.

## Existing rehearsal digests

- Schema digest: `b450092d2e49da353ab02ed784dfb655a135e00c44213cc5fd30782bc2b3b344`
- Replay digest: `c4e899c16f435f74629c9e203d6302c621820ae90e394dd2b66622819999efe7`
- Report digest: `4b97cc9338eb833330572036906447b85f2c3da37da9960f13b850458c979ca9`

This is evidence for the completed disposable rehearsal scope only. It is not
a production-readiness approval.
