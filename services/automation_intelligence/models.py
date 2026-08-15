from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
@dataclass
class AutomationExperience:
    experience_id: str; tenant_id: str; workflow_id: str; incident_type: str = "unknown"; severity: str = "medium"; outcome: str = "unknown"; approval_decision: str = "unknown"; analyst_feedback: str = ""; created_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
@dataclass
class AutomationPerformance:
    workflow_id: str; tenant_id: str; execution_count: int = 0; success_count: int = 0; approval_count: int = 0; rejection_count: int = 0; success_rate: float = 0.0; approval_rate: float = 0.0; confidence: float = 0.0
    def to_dict(self): return asdict(self)
@dataclass
class PlaybookRecommendation:
    recommendation_id: str; tenant_id: str; workflow_id: str; category: str; explanation: str; recommended_change: str; confidence: float = 0.0; requires_human_review: bool = True; created_at: str = field(default_factory=now)
    def to_dict(self): return asdict(self)
