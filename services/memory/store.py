from __future__ import annotations
from copy import deepcopy
class InvestigationMemory:
    """Tenant-scoped memory boundary for investigations and analyst feedback."""
    def __init__(self): self._records = {}
    def remember(self, organization_id, record):
        if not organization_id: raise ValueError("organization_required")
        self._records.setdefault(organization_id, []).append(deepcopy(record)); return record
    def search(self, organization_id, limit=50): return deepcopy(self._records.get(organization_id, [])[-limit:])
    def patterns(self, organization_id): return [r for r in self.search(organization_id) if r.get("type") == "attack_pattern"]
