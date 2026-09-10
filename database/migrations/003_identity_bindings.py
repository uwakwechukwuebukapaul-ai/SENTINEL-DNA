"""Additive external identity binding schema."""

VERSION = 3
DESCRIPTION = "Governed external provider subject to canonical actor bindings"


def upgrade(connection):
    from database.canonical_authority import ensure_canonical_schema
    ensure_canonical_schema(connection, commit=False)
