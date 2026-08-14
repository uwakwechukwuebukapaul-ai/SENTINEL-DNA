from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

class HuntStatus(str, Enum):
    RUNNING = "running"; COMPLETED = "completed"; FAILED = "failed"

@dataclass(frozen=True)
class HuntQuery:
    query: str
    query_type: str = "ioc"
    limit: int = 100
    def __post_init__(self):
        if not isinstance(self.query, str) or not self.query.strip() or len(self.query) > 500: raise ValueError("query must be 1-500 characters")
        if self.query_type not in {"ioc", "evidence", "behavior"}: raise ValueError("unsupported query type")

@dataclass
class HuntFinding:
    category: str
    value: Any
    case_id: str | None = None
    reason: str = ""
    related_investigations: list[str] = field(default_factory=list)

@dataclass
class HuntResult:
    hunt_id: str = field(default_factory=lambda: f"HUNT-{uuid4().hex[:12]}")
    status: HuntStatus = HuntStatus.COMPLETED
    query: HuntQuery | None = None
    findings: list[HuntFinding] = field(default_factory=list)
    queries_executed: int = 0
    duration_ms: float = 0.0
    error: str | None = None
    created_at: str | None = None
    def to_dict(self):
        data = asdict(self); data["status"] = self.status.value; data["query"] = asdict(self.query) if self.query else None
        return data
