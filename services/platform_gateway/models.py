from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

def _now() -> str: return datetime.now(timezone.utc).isoformat()

@dataclass
class APIRequestContext:
    request_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    role: str = "viewer"
    timestamp: str = field(default_factory=_now)
    source: str = "api"
    authenticated: bool = True
    permissions: list[str] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class APIResponse:
    success: bool
    data: Any = None
    error: str | None = None
    request_id: str = ""
    timestamp: str = field(default_factory=_now)
    def to_dict(self) -> dict[str, Any]: return asdict(self)

@dataclass
class ServiceHealth:
    service_name: str
    status: str = "unknown"
    version: str = "1.0"
    last_checked: str = field(default_factory=_now)
    def to_dict(self) -> dict[str, Any]: return asdict(self)
