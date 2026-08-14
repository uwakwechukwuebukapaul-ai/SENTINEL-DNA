from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class Tenant:
    tenant_id: str; name: str; slug: str; status: str="active"; created_at: str=field(default_factory=now); metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return asdict(self)
@dataclass
class TenantUser:
    tenant_id: str; user_id: str; role: str="viewer"; permissions: list[str]=field(default_factory=list); created_at: str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class TenantContext:
    tenant_id: str; user_id: str|None=None; role: str="viewer"; request_id: str=""
    def to_dict(self): return asdict(self)
