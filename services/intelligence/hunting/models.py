from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class HuntingQuery:
    query_id: str
    analyst: str
    query_type: str
    query: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filters: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class HuntResult:
    query_id: str
    matches: list[dict[str, Any]] = field(default_factory=list)
    related_cases: list[str] = field(default_factory=list)
    related_indicators: list[str] = field(default_factory=list)
    confidence: float = 0.0
    summary: str = ""
    synthetic_only: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class ThreatHunt:
    hunt_id: str
    title: str
    hypothesis: str
    techniques: list[str] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class HuntingHypothesis:
    """An advisory hypothesis with explicit evidence basis."""
    hypothesis_id: str
    statement: str
    tenant_id: str
    evidence_references: tuple[str, ...]
    evidence_source: str
    provenance: dict[str, Any]
    confidence: float
    advisory_only: bool = True
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class IOCPivot:
    """A read-only IOC pivot derived from canonical graph relationships."""
    ioc_id: str
    tenant_id: str
    related_entities: tuple[dict[str, Any], ...]
    related_events: tuple[dict[str, Any], ...]
    evidence_references: tuple[str, ...]
    evidence_source: str
    provenance: dict[str, Any]
    confidence: float
    def to_dict(self): return asdict(self)
