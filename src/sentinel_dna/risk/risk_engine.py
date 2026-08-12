from dataclasses import dataclass
from typing import Any

from sentinel_dna.evidence.models import Evidence


@dataclass
class RiskAssessment:
    score: int
    level: str
    reasons: list[str]


class RiskEngine:
    def assess(self, evidence_items: list[Evidence], intelligence: dict[str, Any] | None = None,
               mitre_attack: list[dict[str, Any]] | None = None,
               graph_insights: dict[str, Any] | None = None, uncertainties: list[str] | None = None) -> RiskAssessment:
        score = 0
        reasons = []
        for evidence in evidence_items:
            contribution = int(evidence.confidence * 40)
            score += contribution
            reasons.append(f"{evidence.evidence_type} evidence contributed {contribution} points")
            if evidence.indicators:
                indicator_points = min(25, len(evidence.indicators) * 5)
                score += indicator_points
                reasons.append(f"{len(evidence.indicators)} indicators contributed {indicator_points} points")
            text = f"{evidence.summary} {evidence.raw}".lower()
            if any(term in text for term in ["credential", "password", "mfa", "wire", "malware"]):
                score += 20
                reasons.append("High-risk security terms detected")
        suspicious_iocs = (intelligence or {}).get("threat", {}).get("suspicious_iocs", [])
        if suspicious_iocs:
            score += min(20, len(suspicious_iocs) * 8)
            reasons.append(f"{len(suspicious_iocs)} suspicious IOC reputations increased risk")
        if mitre_attack:
            score += min(15, len(mitre_attack) * 5)
            reasons.append(f"{len(mitre_attack)} MITRE technique mappings increased risk")
        high_confidence = (graph_insights or {}).get("high_confidence_relationships", [])
        if high_confidence:
            score += min(10, len(high_confidence) * 2)
            reasons.append("High-confidence graph relationships increased risk")
        if uncertainties:
            score -= min(10, len(uncertainties) * 2)
            reasons.append("Investigation uncertainty reduced risk certainty")
        score = min(100, score)
        if score >= 75:
            level = "critical"
        elif score >= 50:
            level = "high"
        elif score >= 25:
            level = "medium"
        else:
            level = "low"
        return RiskAssessment(score=score, level=level, reasons=reasons)
