"""Additive canonical identity authority schema."""

VERSION = 2
DESCRIPTION = "Canonical tenants, identities, memberships, and authority metadata"


def upgrade(connection):
    from database.canonical_authority import ensure_canonical_schema
    ensure_canonical_schema(connection)

