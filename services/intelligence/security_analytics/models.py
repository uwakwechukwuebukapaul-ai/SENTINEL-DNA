from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

@dataclass
class SecurityMetricSnapshot:
    snapshot_id: str
    tenant_id: str | None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, float] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class TrendAnalysis:
    metric: str
    direction: str
    change: float
    confidence: float
    summary: str
    def to_dict(self): return asdict(self)

@dataclass
class SecurityAnomaly:
    anomaly_id: str
    tenant_id: str | None
    metric: str
    observed: float
    baseline: float
    severity: str
    summary: str
    def to_dict(self): return asdict(self)

@dataclass
class ForecastResult:
    tenant_id: str | None
    risk_direction: str
    expected_posture_change: float
    horizon: str = "next_period"
    recommended_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    def to_dict(self): return asdict(self)
