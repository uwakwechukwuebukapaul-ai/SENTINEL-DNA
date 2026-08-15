from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class User:
    user_id: str; tenant_id: str; username: str; email: str; display_name: str = ""; status: str = "active"; roles: list[str] = field(default_factory=list); created_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class Tenant:
    tenant_id: str; name: str; status: str = "active"; settings: dict[str, Any] = field(default_factory=dict); created_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class Role:
    role_id: str; name: str; description: str = ""; permissions: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)
@dataclass
class Permission:
    permission_id: str; resource: str; action: str; description: str = ""
    def to_dict(self): return asdict(self)
@dataclass
class Session:
    session_id: str; user_id: str; tenant_id: str; created_at: str = field(default_factory=now); expires_at: str = ""; active: bool = True
    def to_dict(self): return asdict(self)
