from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any
from uuid import uuid4
from services.memory import InvestigationMemory
@dataclass
class DecisionRecord:
    decision: str; confidence: float; evidence: list[Any]; reasoning: list[str]; recommended_action: str; id: str = field(default_factory=lambda: str(uuid4()))
    def public(self): return asdict(self)
class EvidenceAnalyzer:
    def analyze(self, alert, evidence): return {"count": len(evidence or []), "alert": alert or {}, "signals": [item.get("type", "evidence") for item in evidence or [] if isinstance(item, dict)]}
class AttackPatternAnalyzer:
    def analyze(self, alert, iocs, memory):
        techniques = (alert or {}).get("techniques", []) or (alert or {}).get("mitre_techniques", [])
        return {"techniques": techniques, "ioc_count": len(iocs or []), "related_patterns": memory}
class ThreatHypothesisGenerator:
    def generate(self, alert, patterns): return "malicious_activity" if patterns.get("techniques") or patterns.get("ioc_count") else "insufficient_evidence"
class ConfidenceEvaluator:
    def evaluate(self, evidence, patterns): return round(min(0.99, 0.25 + evidence["count"] * 0.1 + bool(patterns["techniques"]) * 0.25 + min(patterns["ioc_count"], 3) * 0.1), 2)
class DecisionEngine:
    def decide(self, hypothesis, confidence):
        action = "contain_and_investigate" if hypothesis == "malicious_activity" and confidence >= 0.6 else "collect_more_evidence"
        return DecisionRecord("escalate" if action.startswith("contain") else "monitor", confidence, [], [f"Hypothesis: {hypothesis}", f"Confidence threshold evaluated at {confidence:.0%}"], action)
class AutonomousInvestigationEngine:
    def __init__(self, memory=None): self.memory = memory or InvestigationMemory()
    def investigate(self, organization_id, alert, evidence=None, iocs=None, previous_incidents=None):
        evidence_result = EvidenceAnalyzer().analyze(alert, evidence or []); patterns = AttackPatternAnalyzer().analyze(alert, iocs or [], previous_incidents or self.memory.patterns(organization_id)); hypothesis = ThreatHypothesisGenerator().generate(alert, patterns); confidence = ConfidenceEvaluator().evaluate(evidence_result, patterns); decision = DecisionEngine().decide(hypothesis, confidence); decision.evidence = evidence or []; decision.reasoning.extend([f"Observed {evidence_result['count']} evidence items", f"Mapped {len(patterns['techniques'])} MITRE techniques"]); result = {"hypothesis": hypothesis, "attack_story": f"{hypothesis} supported by {evidence_result['count']} evidence items", "techniques": patterns["techniques"], "iocs": iocs or [], "decision": decision.public(), "recommendations": [decision.recommended_action]}; self.memory.remember(organization_id, {"type": "investigation", **result}); return result
