# Evidence-only deployment contract validation

`deployment/validation/contract.py` is an offline validation boundary. Its
`MigrationRehearsalService` and `BackupRecoveryValidationService` are
read-only operational proof services; the contract validator composes their
safe results. It
answers whether deployment evidence is complete and internally consistent; it
does not authorize, deploy, start, stop, migrate, restore, or enforce an
investigation verdict.

## Contracts

The validator evaluates five independent contracts:

1. **Runtime configuration** uses the existing protected configuration
   verifier. Secret values are read in memory and represented only by safe
   error codes and variable names.
2. **Production startup** validates the production `RuntimeConfig` projection
   and the checked-in WSGI/Docker startup shape: production mode, the
   non-root user, and the single-worker SQLite boundary.
3. **Database migration rehearsal** loads numbered migrations into an
   in-memory SQLite database, checks ordering, source digests, `VERSION`,
   `DESCRIPTION`, and `upgrade`, applies the full upgrade path, replays it for
   idempotency, and exercises a synthetic transaction failure. Application
   databases are never opened or changed. Migrations are treated as
   forward-only: rollback is not inferred from a missing `down()` function;
   operational rollback means restoring a validated pre-migration backup.
4. **Deployment artifact integrity** checks Docker build-context policy and
   the Compose boundary. If supplied, a release manifest is verified against
   the current checkout and expected image digest.
5. **Backup/restore readiness** can rehearse backup creation from a supplied
   database copy, validates the backup artifact and manifest, restores into a
   disposable temporary target, compares logical content digests across
   source/backup/restore, and checks tenant columns, provenance columns,
   integrity checks, and append-only audit triggers. Rows are never placed in
   the report; only safe digests and bounded inventory metadata are retained.

## Evidence and replay

Reports contain a validation status, per-contract checks, safe evidence, safety
invariants, a report digest, and a deterministic replay digest. The replay
digest excludes timestamps, host paths, and timing. Replaying the same
checkout and evidence therefore produces the same replay digest even though a
new report digest may be produced.

`write_immutable_report()` requires an existing non-symlink parent outside the
repository and refuses an existing target or temporary file. This is the
append-only evidence boundary: a prior report cannot be replaced by a later
run. The CLI prints the report and returns non-zero on any failed contract.

## Safety boundary

The validator has no calls to authorization, verdict, investigation
coordination, orchestration, or runtime task execution services. It does not
modify `InvestigationCoordinator`, `InvestigationOrchestrator`,
`RuntimeTaskExecutor`, or `InvestigationResult`. A protected-file custody
check reports a dirty protected boundary as inconclusive. Tenant isolation,
audit integrity, fail-closed behavior, and append-only evidence remain
properties of the existing application services; this layer only records
whether its own observational boundary preserved them.

Example (PowerShell):

```powershell
python deployment/scripts/validate_deployment_contract.py `
  --env-file C:\ProgramData\Sentinel-DNA\protected.env `
  --release-manifest C:\ProgramData\Sentinel-DNA\release\manifest.json `
  --backup-source C:\ProgramData\Sentinel-DNA\backups\source.sqlite `
  --backup-artifact C:\ProgramData\Sentinel-DNA\backups\candidate.sqlite `
  --backup-manifest C:\ProgramData\Sentinel-DNA\backups\candidate.json `
  --output C:\ProgramData\Sentinel-DNA\evidence\deployment-contract.json
```

No `docker compose`, deployment adapter, external provider, or production
database operation is invoked by this command.
