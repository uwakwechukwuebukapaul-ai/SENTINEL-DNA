# Sentinel DNA Operational Readiness Evidence

This document is the canonical repository-side evidence boundary for the
controlled operational-readiness exercise. It does not authorize deployment,
provider activation, credential handoff, or production mutation.

## Certified artifact

| Artifact | Value |
| --- | --- |
| Commit | `8eef9afd588a1dda80975bb997e4baae06a1d06d` |
| Git tree | `6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a` |
| Persistence authority | SQLite at the operator-supplied `SENTINEL_DNA_DB_PATH` |
| Worker model | Explicitly started, single-node, fail-closed authorization |
| Autonomous boundary | One read-only follow-up; `max_iterations = 1` |

## Backup and restore procedure

Use an operator-selected directory outside the repository. The commands below
never print rows, credentials, tokens, provider payloads, or private keys:

```powershell
python deployment/scripts/sqlite_backup.py backup `
  --source <AUTHORITATIVE_SQLITE_PATH> `
  --artifact <BACKUP_DIRECTORY>\soc.sqlite `
  --manifest <BACKUP_DIRECTORY>\soc.sqlite.json `
  --commit 8eef9afd588a1dda80975bb997e4baae06a1d06d `
  --tree 6ca1c289586f84e93d5e9bb29fa4490f3dfbae9a

python deployment/scripts/sqlite_backup.py validate `
  --artifact <BACKUP_DIRECTORY>\soc.sqlite `
  --manifest <BACKUP_DIRECTORY>\soc.sqlite.json

python deployment/scripts/sqlite_backup.py restore `
  --artifact <BACKUP_DIRECTORY>\soc.sqlite `
  --manifest <BACKUP_DIRECTORY>\soc.sqlite.json `
  --target <ISOLATED_RESTORE_DIRECTORY>\soc.sqlite
```

The manifest records only safe metadata: artifact identity, size, SHA-256,
creation time, SQLite integrity result, schema fingerprint, table names and
counts, source commit, and source tree. Existing artifacts and restore targets
are never overwritten.

The authoritative SQLite file includes the durable cases, evidence, timeline,
IOC, investigation, execution, job, snapshot, sufficiency, follow-up,
ProviderObservation, quota, idempotency, audit, tenant, authorization, and
provenance state where those repositories are initialized. Process-local caches
are not authoritative backup material.

## Restore certification requirements

An isolated restore must verify:

1. SHA-256 and manifest identity.
2. SQLite `integrity_check` and schema fingerprint.
3. Deterministic table counts.
4. Investigation job and execution identity preservation.
5. ProviderObservation and audit sequence preservation.
6. Quota and idempotency preservation.
7. Tenant A/B positive and negative access checks.
8. Cross-tenant replay and investigation access denial.
9. Application health/readiness against the isolated database.

No restore may overwrite the authoritative database during certification.

## Recovery targets and limitations

Repository-controlled tooling can prove artifact integrity and isolated file
restoration. It does not by itself establish production backup scheduling,
volume durability, external secret/TLS custody, host recovery, or operator
availability.

RPO and RTO must be measured by an authorized operator using a disposable
isolated environment. No production RPO/RTO value is claimed by this document.

## Worker and observability boundary

The durable worker is explicitly started and requires a non-empty service
identity plus an affirmative authorization hook. Flask does not start it.
Worker claim, lease, heartbeat, retry, cancellation, timeout, stale-worker
protection, and bounded-follow-up behavior are repository-tested. Production
process supervision, log shipping, alerting, and worker operations remain
external operational gates.

## TLS, secrets, and trusted metadata

The checked-in Nginx configuration is localhost-only validation configuration.
Production hostname, CA certificate, private-key custody, trusted release
metadata, ACLs, DNS, and firewall evidence must be supplied externally. No
production TLS material or credentials belong in this repository or in backup
manifests.

## Current certification status

- V2.1 engineering: **COMPLETE**.
- Release-manifest/source certification: **PASS** for the certified tree.
- SQLite backup/restore implementation: **IMPLEMENTED; synthetic isolated drill PASS**.
- Synthetic drill evidence: SQLite integrity `ok`, RPO `0.0s` under a no-write
  post-backup condition, and local RTO approximately `0.018s` on the review
  host. These values are not production targets.
- Production backup/restore: **EXTERNAL OPERATIONAL GATE**.
- Production worker operation: **EXTERNAL OPERATIONAL GATE**.
- Production TLS and secret custody: **EXTERNAL OPERATIONAL GATE**.
- Production deployment authorization: **NOT GRANTED**.
