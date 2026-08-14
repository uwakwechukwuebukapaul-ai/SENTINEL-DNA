from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class IntegrationConnector:
    connector_id: str; name: str; provider: str; connector_type: str; status: str="offline"; enabled: bool=False; configuration: dict[str,Any]=field(default_factory=dict); created_at: str=field(default_factory=now); synthetic_only: bool=True
    def to_dict(self): return asdict(self)
@dataclass
class IntegrationCredential:
    credential_id: str; connector_id: str; credential_type: str; encrypted_reference: str; created_at: str=field(default_factory=now); rotated_at: str|None=None
    def to_dict(self): return asdict(self)
@dataclass
class IntegrationHealth:
    connector_id: str; status: str; last_check: str; latency: float=0.0; error_count: int=0; message: str=""
    def to_dict(self): return asdict(self)
@dataclass
class IntegrationEvent:
    event_id: str; connector_id: str; event_type: str; payload_reference: str; timestamp: str=field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class CredentialRef:
    """Reference to encrypted credentials; plaintext secrets never leave this boundary."""
    provider: str
    encrypted_payload: str
    key_version: str = "v1"
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=now)
    def public(self): return {"id": self.id, "provider": self.provider, "key_version": self.key_version, "created_at": self.created_at}
@dataclass
class Integration:
    name: str
    provider: str
    kind: str
    config: dict[str, Any] = field(default_factory=dict)
    credential: CredentialRef | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "unknown"
    last_checked_at: str | None = None
    last_error: str | None = None
    def public(self):
        value = asdict(self); value["credential"] = self.credential.public() if self.credential else None; return value
