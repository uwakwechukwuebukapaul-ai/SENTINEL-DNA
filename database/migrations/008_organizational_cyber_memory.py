"""Organizational cyber memory records and append-only audit evidence."""

VERSION = 8
DESCRIPTION = "Tenant-scoped organizational cyber memory foundation"


def upgrade(connection):
    from database.portability import append_only_statements, execute_script

    execute_script(
        connection,
        """
        CREATE TABLE IF NOT EXISTS organizational_memory (
            record_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            source_investigation_id TEXT NOT NULL,
            created_by TEXT,
            confidence REAL NOT NULL,
            observed_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            why_stored TEXT NOT NULL,
            evidence_provenance TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            audit_hash TEXT NOT NULL,
            advisory_only INTEGER NOT NULL DEFAULT 1 CHECK (advisory_only IN (0, 1))
        );
        CREATE INDEX IF NOT EXISTS idx_org_memory_tenant_type
            ON organizational_memory(tenant_id, memory_type, created_at, record_id);
        CREATE INDEX IF NOT EXISTS idx_org_memory_tenant_investigation
            ON organizational_memory(tenant_id, source_investigation_id, created_at);
        CREATE TABLE IF NOT EXISTS organizational_memory_audit (
            audit_id TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            event_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_org_memory_audit_tenant
            ON organizational_memory_audit(tenant_id, created_at, audit_id);
        """
    )
    backend = getattr(connection, "backend_name", "sqlite")
    for table_name, prefix, message in (
        ("organizational_memory", "organizational_memory_append_only", "organizational_memory_is_append_only"),
        ("organizational_memory_audit", "organizational_memory_audit_append_only", "organizational_memory_audit_is_append_only"),
    ):
        for statement in append_only_statements(
            backend,
            table_name=table_name,
            trigger_prefix=prefix,
            error_message=message,
        ):
            connection.execute(statement)
