from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

def now(): return datetime.now(timezone.utc).isoformat()
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
