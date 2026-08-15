"""Structured analyst feedback and deterministic quality signals."""
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from hashlib import sha256

AGREEMENT={"agree","partially_agree","disagree","unable_to_assess"}
EVIDENCE={"sufficient","partially_sufficient","insufficient","unable_to_assess"}
USEFULNESS={"useful","partially_useful","not_useful","not_applicable"}
def _now(): return datetime.now(timezone.utc).isoformat()
@dataclass(frozen=True)
class AnalystInvestigationFeedback:
    feedback_id: str; tenant_id: str; investigation_id: str; outcome_reference: str = ""; analyst_reference: str = ""
    outcome_agreement: str = "unable_to_assess"; evidence_sufficiency: str = "unable_to_assess"; recommendation_usefulness: str = "not_applicable"
    confidence: float | None = None; reason_codes: list = field(default_factory=list); supporting_references: list = field(default_factory=list)
    provenance: dict = field(default_factory=dict); created_at: str = field(default_factory=_now)
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class InvestigationQualitySignal:
    status: str; dimensions: dict = field(default_factory=dict); reasons: list = field(default_factory=list); feedback_count: int = 0
    uncertainty: list = field(default_factory=list); advisory_only: bool = True; provenance: dict = field(default_factory=dict)
    def to_dict(self): return asdict(self)
def stable_feedback_id(tenant_id, investigation_id, index): return sha256(f"{tenant_id}|{investigation_id}|{index}".encode()).hexdigest()[:24]
