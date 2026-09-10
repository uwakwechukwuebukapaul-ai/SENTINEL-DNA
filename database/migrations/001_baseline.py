"""Create the normalized core schema for a new or existing database."""
VERSION = 1
DESCRIPTION = "normalized_core_schema"

def upgrade(connection):
    from database.schema import core_schema_statements

    backend = getattr(connection, "backend_name", "sqlite")
    for statement in core_schema_statements(backend)[1:]:
        connection.execute(statement)
