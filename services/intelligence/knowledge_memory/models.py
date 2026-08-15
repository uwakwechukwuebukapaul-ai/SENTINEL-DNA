from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class KnowledgeRecord:
    record_id: str
    tenant_id: str | None
    source: str
    content: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)

@dataclass
class InvestigationMemory:
    record_id: str
    tenant_id: str | None
    investigation_id: str
    outcome: str
    evidence: list[str] = field(default_factory=list)
    techniques: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class SecurityPattern:
    pattern_id: str
    tenant_id: str | None
    name: str
    occurrences: int
    indicators: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class LessonLearned:
    lesson_id: str
    tenant_id: str | None
    lesson: str
    rationale: str
    source_record_ids: list[str] = field(default_factory=list)
    advisory_only: bool = True
    def to_dict(self): return asdict(self)
