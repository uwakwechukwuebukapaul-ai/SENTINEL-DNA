# PostgreSQL remediation custody reconciliation

## Snapshot

- Branch: `remediation/postgresql-production-readiness`
- Remediation HEAD: `94e3da4f4fa3952981fb68e9d0d3205ec6aa6a7c`
- Protected RC1 commit: `30c9568012879319675a4c86eeb712519f61dfe3`
- RC1 tag target: verified unchanged at `30c9568012879319675a4c86eeb712519f61dfe3`
- Production deployment: not performed
- Production database usage: not performed by the rehearsal
- External PostgreSQL evidence: `C:\Temp\sentinel-dna-postgres-full-rehearsal.json`

## Dirty-worktree disposition

The worktree is intentionally dirty and contains the remediation changes,
portability/migration utilities, rehearsal package, tests, and remediation
documentation. It is not a clean release custody state. The shared Git
metadata remains non-writable for committing, so no commit was forced or
created.

The dirty state is reconciled for evidence review as follows:

- the rehearsal report HEAD matches the remediation HEAD above;
- the report records `worktree_dirty: true`;
- the report is external to the repository;
- no RC1 ref, release tag, deployment artifact, or production configuration
  was changed by the evidence review;
- `git diff --check` passes, apart from normal line-ending warnings;
- final release custody remains blocked until the remediation diff is
  independently reviewed and committed or otherwise formally attested in
  writable Git metadata.

## Stale-evidence reconciliation

The package status was updated to reference the completed external PostgreSQL
report. Historical phase documents retain their historical scope; they are
not evidence of production readiness. The current Phase 7 document records
the completed disposable rehearsal and explicitly retains the unexecuted
backup/restore, credential, monitoring/ownership, and stale-evidence gates.

## Decision

Custody is reconciled for continued remediation review, not for release
approval. No production-readiness claim is made.
