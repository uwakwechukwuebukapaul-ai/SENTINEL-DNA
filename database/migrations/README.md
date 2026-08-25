# Sentinel DNA database migrations

Migrations are additive and versioned. Existing startup `CREATE TABLE IF NOT EXISTS` initialization remains compatible while deployments can record applied versions in a future migration runner.

## Version 001

The baseline schema is the current schema created by `database.models.create_tables()` and service repositories. No destructive migration is required for this foundation release.

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
