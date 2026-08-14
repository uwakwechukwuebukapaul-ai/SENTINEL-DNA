"""Baseline migration marker; existing schemas require no SQL changes."""
VERSION = 1
DESCRIPTION = "Baseline existing Sentinel DNA schema"

def upgrade(connection):
    connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
