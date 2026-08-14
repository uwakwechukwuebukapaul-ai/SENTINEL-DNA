from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class ExecutionNode:
    name: str
    status: str = "pending"
    priority: str = "medium"
    dependencies: list[str] = field(default_factory=list)
    result: Any = None

    def public(self) -> dict:
        return {"name": self.name, "status": self.status, "priority": self.priority, "dependencies": list(self.dependencies), "result": self.result}

@dataclass
class ExecutionGraph:
    case_id: str
    nodes: list[ExecutionNode] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def public(self) -> dict:
        return {"case_id": self.case_id, "nodes": [node.public() for node in self.nodes], "created_at": self.created_at}
