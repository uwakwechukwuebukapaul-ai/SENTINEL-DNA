"""Governed provider-tenant trust resolution and lifecycle."""
from __future__ import annotations
from dataclasses import dataclass
from database.canonical_authority import CanonicalMembershipRepository, CanonicalTenantRepository, CanonicalUnitOfWork, ProviderTenantTrustRepository
from database.connection import DatabaseConnection, database

class ProviderTenantTrustError(ValueError): pass

@dataclass(frozen=True)
class ProviderTenantTrust:
    trust_id: str; provider: str; issuer: str; external_tenant_id: str; canonical_tenant_id: str; status: str; created_by: str; revoked_at: str | None

def _trust(row): return ProviderTenantTrust(row["trust_id"], row["provider"], row["issuer"], row["external_tenant_id"], row["canonical_tenant_id"], row["status"], row["created_by"], row["revoked_at"]) if row else None

class ProviderTenantTrustService:
    ADMIN_PERMISSION = "provider.tenant_trust.manage"
    def __init__(self, authorization=None, db: DatabaseConnection = database, audit=None): self.authorization, self.db, self.audit = authorization, db, audit
    def create(self, context, provider, issuer, external_tenant_id, canonical_tenant_id, created_by):
        values = [str(v or "").strip() for v in (provider, issuer, external_tenant_id, canonical_tenant_id, created_by)]
        if not all(values) or not issuer.startswith("https://"): raise ProviderTenantTrustError("trust_fields_invalid")
        with CanonicalUnitOfWork(self.db) as unit:
            self._authorize(context, canonical_tenant_id, unit.conn)
            if not CanonicalTenantRepository(unit.conn).get(canonical_tenant_id): raise ProviderTenantTrustError("canonical_tenant_not_found")
            try: row = ProviderTenantTrustRepository(unit.conn).create(*values)
            except Exception as exc: raise ProviderTenantTrustError("provider_tenant_trust_rejected") from exc
            self._audit(unit.conn, "PROVIDER_TENANT_TRUST_CREATED", row, context); return _trust(row)
    def resolve(self, provider, issuer, external_tenant_id):
        with CanonicalUnitOfWork(self.db) as unit: row = ProviderTenantTrustRepository(unit.conn).get(str(provider or ""), str(issuer or ""), str(external_tenant_id or "")); trust = _trust(row); tenant = CanonicalTenantRepository(unit.conn).get(trust.canonical_tenant_id) if trust else None
        if not trust or trust.status != "active" or not tenant or tenant["status"] != "active": raise ProviderTenantTrustError("provider_tenant_trust_denied")
        return trust
    def disable(self, context, trust_id): return self._transition(context, trust_id, "disabled")
    def reactivate(self, context, trust_id): return self._transition(context, trust_id, "active")
    def revoke(self, context, trust_id): return self._transition(context, trust_id, "revoked")
    def _authorize(self, context, tenant_id, connection):
        if not self.authorization: raise PermissionError("canonical_authorization_required")
        self.authorization.require_permission(context, tenant_id, self.ADMIN_PERMISSION)
    def _transition(self, context, trust_id, status):
        with CanonicalUnitOfWork(self.db) as unit:
            repo = ProviderTenantTrustRepository(unit.conn); current = repo.get_by_id(trust_id)
            if not current: raise ProviderTenantTrustError("provider_tenant_trust_not_found")
            self._authorize(context, current["canonical_tenant_id"], unit.conn)
            allowed = {"active": {"disabled", "revoked"}, "disabled": {"active", "revoked"}, "revoked": set()}
            if status not in allowed[current["status"]]: raise ProviderTenantTrustError("invalid_trust_transition")
            row = repo.set_status(trust_id, status); self._audit(unit.conn, "PROVIDER_TENANT_TRUST_" + status.upper(), row, context); return _trust(row)
    def _audit(self, connection, event, row, context):
        if self.audit: self.audit.record(event, details={"trust_id": row["trust_id"], "provider": row["provider"], "issuer": row["issuer"], "external_tenant_id": row["external_tenant_id"], "canonical_tenant_id": row["canonical_tenant_id"], "acting_actor_id": context.actor_id if context else ""}, connection=connection)
