from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class SOCWorkspaceSnapshot:
    generated_at: str
    active_cases: int = 0
    high_risk_cases: int = 0
    critical_cases: int = 0
    threat_campaigns: int = 0
    active_hunts: int = 0
    average_ai_confidence: float = 0.0
    investigation_metrics: dict[str, Any] = field(default_factory=dict)
    synthetic_only: bool = True
    def to_dict(self): return asdict(self)

@dataclass
class CaseWorkspaceView:
    case_id: str
    severity: str = "unknown"
    status: str = "unknown"
    evidence_summary: Any = None
    threat_intelligence_summary: Any = None
    hunting_summary: Any = None
    reasoning_summary: Any = None
    decision_summary: Any = None
    copilot_summary: Any = None
    narrative_summary: Any = None
    def to_dict(self): return asdict(self)

@dataclass
class ThreatPostureSummary:
    total_cases: int = 0
    threat_score_average: float = 0.0
    top_indicators: list[str] = field(default_factory=list)
    top_campaigns: list[str] = field(default_factory=list)
    top_mitre_techniques: list[str] = field(default_factory=list)
    risk_distribution: dict[str, int] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class DetectionPostureSummary:
    total_rules: int = 0
    sigma_rules: int = 0
    mitre_coverage: Any = None
    detection_gaps: list[Any] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)
