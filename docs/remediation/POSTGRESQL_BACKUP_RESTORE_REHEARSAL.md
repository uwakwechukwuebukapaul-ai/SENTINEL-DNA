# PostgreSQL backup/restore rehearsal package

This runbook includes a bounded manual evidence record. It applies only to
synthetic disposable PostgreSQL instances. It does not use `DATABASE_URL`, a
production host, or customer data.

## Required isolation

- Use separate Compose project names and host ports for source and restore
  lifecycles.
- Use PostgreSQL 16-compatible `pg_dump`, `pg_restore`, and client tools.
- Keep dump files, checksums, logs, and reports outside the repository.
- Do not serialize passwords or connection URLs in evidence.
- Record the remediation HEAD at execution time and require independent
  custody review before release use.

## Execution checklist

1. Record operator, reviewer, UTC start time, remediation HEAD, Compose project
   names, image digest, and external artifact directory.
2. Start a fresh disposable source PostgreSQL instance and verify it is empty.
3. Run the authorized full rehearsal and retain its external report.
4. Create a custom-format dump to an external path. Record its SHA-256 and
   byte count without printing the connection string.
5. Start a separate empty disposable restore instance on another port.
6. Restore with errors treated as fatal.
7. Compare schema inventory and schema digest against the source report.
8. Compare migration state, synthetic record counts, tenant isolation,
   provenance, audit integrity, and application compatibility.
9. Discard only the disposable restore lifecycle and confirm source evidence
   remains unchanged.
10. Obtain independent review of checksums, digests, logs, and custody.

## Manual evidence record

The following facts were supplied manually:

- Source container: `sentinel-dna-postgres-rehearsal-postgres-1`
- Backup artifact: `C:\Temp\sentinel-dna-rehearsal.dump`
- Backup SHA-256: `BC6932E9194F38526EC75982F681D253C0764B951A9A8B4D4CA3B5C3FB1FE4D4`
- Backup result: `pg_dump` custom format completed successfully
- Restore target: `sentinel_restore_test`
- Restore result: `pg_restore` completed successfully
- Restore validation: `schema_migrations` count was `1`
- Production `DATABASE_URL`: not used
- Customer data: not used
- Remediation HEAD: `94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`

The following were not supplied and are not inferred:

- dump SHA-256 and byte count;
- source/restore schema digest comparison;
- full migration-state comparison beyond `schema_migrations` count `1`;
- application compatibility validation after restore;
- tenant, provenance, and audit comparison after restore;
- restore rollback result;
- independent reviewer and worktree custody attestation.

This establishes successful dump and restore commands for the stated
disposable scope. The supplied dump checksum, successful restore, and
`schema_migrations` validation close the documented backup/restore rehearsal
scope. The broader production-like gate remains subject to final custody and
operational review.
