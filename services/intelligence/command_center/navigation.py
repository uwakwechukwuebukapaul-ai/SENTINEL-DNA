from dataclasses import dataclass, field
from datetime import datetime, timezone

def _now(): return datetime.now(timezone.utc).isoformat()

@dataclass
class NavigationTarget:
    target_type: str; target_id: str; tenant_id: str; source_domain: str = "command_center"
    parent_context: dict = field(default_factory=dict); breadcrumb: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict); timestamp: str = field(default_factory=_now)
    def to_dict(self): return self.__dict__.copy()

class NavigationBuilder:
    def target(self, tenant_id, target_type, target_id, source_domain="command_center", parent=None, provenance=None):
        parent=parent or {}; crumbs=list(parent.get("breadcrumb", [])); crumbs.append({"type":target_type,"id":target_id})
        return NavigationTarget(target_type, str(target_id), tenant_id, source_domain, parent, crumbs, dict(provenance or {}))
