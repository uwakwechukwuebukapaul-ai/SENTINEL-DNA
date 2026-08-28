"""Additive governed provider-to-canonical-tenant trust schema."""
VERSION = 4
DESCRIPTION = "Governed OIDC provider tenant trust"
def upgrade(connection):
    from database.canonical_authority import ensure_canonical_schema
    ensure_canonical_schema(connection, commit=False)
