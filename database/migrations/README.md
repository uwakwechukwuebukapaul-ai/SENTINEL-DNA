# Sentinel DNA database migrations

Migrations are additive, versioned, and authoritative for deployment database
state. `database/migrations/registry.py` is the only registry: it loads the
checked-in modules in version order and rejects duplicate or non-contiguous
versions. `database/run_migrations.py` is the deployment command and records
successful versions in `schema_migrations`.

The runner also supports a separate namespace registry for future migrations.
Namespace migrations use the immutable `(namespace, migration_key)` identity
and are recorded in `migration_records`; they never reuse or reinterpret
legacy numeric versions. The namespace registry contains only explicitly
approved foundation and future migrations; later migrations remain
unregistered until separately approved.

Namespace execution validates the complete dependency graph before opening
database work, uses a PostgreSQL transaction advisory lock or SQLite
`BEGIN IMMEDIATE`, and records execution metadata in the same transaction as
the migration. A committed `applying` record is invalid; failed work rolls
back both schema and metadata.

The approved Entra binding migration is `future.entra_identity_bindings` and
depends on `foundation.users_authority`. It stores the verified identity tuple
`(issuer, tenant_id, object_id, subject_id)`, with database-enforced uniqueness
for active tuples and at most one active binding per local user. Stored states
are `active` and `revoked` (the documented ACTIVE and REVOKED states). A
revoked binding cannot be reactivated; a replacement requires a new binding
record and an explicit transaction. The migration does not create, register,
or execute numeric migration 011.

Older application binaries do not understand `migration_records`. They can
continue reading legacy `schema_migrations`, but deployment policy must keep
an older binary from serving a database that requires namespace-aware
ownership guarantees.

The runner executes the complete chain in one transaction on PostgreSQL and
SQLite. Re-running it is safe and applies no versions that are already
recorded. The application WSGI import path does not run this chain; deployment
must run the one-shot Compose `migration` service before starting or replacing
the app.

## Version 001

The baseline migration creates the normalized core schema from
`database.schema.core_schema_statements()`. No destructive migration is
required for this foundation release. The legacy `database.models.create_tables`
API remains available for SQLite development compatibility.

## Version 007

`007_investigation_memory.py` adds tenant-scoped investigation memory,
append-only analyst feedback, provenance-bearing audit events, and deterministic
indexes for historical retrieval. The migration is additive and keeps the
canonical investigation execution/result contracts unchanged.

## Version 008

`008_organizational_cyber_memory.py` adds tenant-scoped organizational
patterns, campaign memories, analyst knowledge, detection learning, response
playbook memories, and append-only memory audit evidence. Records retain their
source investigation, evidence provenance, attribution, confidence, timestamps,
and immutable content hashes. The records are advisory only.

## Optional Version 010

`010_controlled_analyst_pilot.py` is an explicitly selected controlled
analyst-pilot overlay. It adds tenant lifecycle events, analyst membership
events, immutable feedback, review events, and a hash-linked pilot audit
stream. It is intentionally absent from `MIGRATIONS`, `STAGING_MIGRATIONS`,
and the Gate 4 custody chain. Select
`CONTROLLED_ANALYST_PILOT_MIGRATIONS` only for a controlled pilot deployment.
