from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class CaseEvent:
    event_type: str
    message: str
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Case:
    title: str
    description: str
    severity: str = "medium"
    status: str = "open"
    case_id: str = field(default_factory=lambda: f"case-{uuid4().hex[:12]}")
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    evidence_ids: list[str] = field(default_factory=list)
    events: list[CaseEvent] = field(default_factory=list)

    def add_event(self, event_type: str, message: str, metadata: dict[str, Any] | None = None) -> None:
        self.events.append(CaseEvent(event_type=event_type, message=message, metadata=metadata or {}))
        self.updated_at = utc_now_iso()

    def attach_evidence(self, evidence_id: str) -> None:
        if evidence_id not in self.evidence_ids:
            self.evidence_ids.append(evidence_id)
            self.add_event("evidence_attached", f"Attached evidence {evidence_id}")

