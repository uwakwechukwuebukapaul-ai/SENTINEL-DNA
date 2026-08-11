from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class Evidence:
    source: str
    evidence_type: str
    summary: str
    raw: dict[str, Any]
    confidence: float = 0.5
    evidence_id: str = field(default_factory=lambda: f"ev-{uuid4().hex[:12]}")
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    indicators: list[str] = field(default_factory=list)

