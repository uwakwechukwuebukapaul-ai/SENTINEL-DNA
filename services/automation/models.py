from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

APPROVAL_STATES = {"pending", "approved", "rejected"}
SAFE_ACTIONS = {"enrich_ioc", "create_analyst_notification", "create_case_task", "generate_investigation_request"}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class Playbook:
    name: str
    steps: list[dict[str, Any]]
    description: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=utc_now)
    enabled: bool = True

    def public(self) -> dict[str, Any]: return asdict(self)

@dataclass
class Execution:
    playbook_id: str
    requested_by: int | None
    input: dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    status: str = "pending_approval"
    approval: str = "pending"
    results: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    completed_at: str | None = None

    def public(self) -> dict[str, Any]: return asdict(self)
