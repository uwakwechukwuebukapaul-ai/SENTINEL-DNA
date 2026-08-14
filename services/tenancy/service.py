from __future__ import annotations
from .models import Organization
class TenancyService:
    """Tenant persistence boundary; memberships are isolated by organization_id."""
    def __init__(self): self.organizations = {}; self.memberships = {}
    def create(self, name, tier="trial", owner_id=None):
        if not str(name).strip(): raise ValueError("organization_name_required")
        org = Organization(str(name).strip(), str(tier or "trial")); self.organizations[org.organization_id] = org
        if owner_id is not None: self.memberships.setdefault(org.organization_id, {})[str(owner_id)] = "admin"
        return org
    def get(self, organization_id): return self.organizations.get(organization_id)
    def for_user(self, user_id): return [org for oid, org in self.organizations.items() if str(user_id) in self.memberships.get(oid, {})]
    def users(self, organization_id): return [{"user_id": uid, "role": role} for uid, role in self.memberships.get(organization_id, {}).items()]
    def role(self, organization_id, user_id): return self.memberships.get(organization_id, {}).get(str(user_id))
