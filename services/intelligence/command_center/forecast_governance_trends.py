"""Immutable governance trend interpretation."""
from dataclasses import asdict, dataclass
@dataclass(frozen=True)
class ForecastGovernanceTrend:
    tenant_id: str; trend_id: str; governance_trend: str="insufficient_history"; reliability_trend: str="insufficient_history"; calibration_trend: str="insufficient_history"; drift_trend: str="insufficient_history"; risk_trend: str="insufficient_history"; recurring_signals: tuple=(); uncertainty: tuple=(); provenance: tuple=(); advisory_only: bool=True
    def to_dict(self): return asdict(self)
