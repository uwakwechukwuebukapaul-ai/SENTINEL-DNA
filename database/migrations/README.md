# Sentinel DNA database migrations

Migrations are additive and versioned. Existing startup `CREATE TABLE IF NOT EXISTS` initialization remains compatible while deployments can record applied versions in a future migration runner.

## Version 001

The baseline schema is the current schema created by `database.models.create_tables()` and service repositories. No destructive migration is required for this foundation release.
