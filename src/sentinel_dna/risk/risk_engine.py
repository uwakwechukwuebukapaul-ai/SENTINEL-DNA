from dataclasses import dataclass

from sentinel_dna.evidence.models import Evidence


@dataclass
class RiskAssessment:
    score: int
    level: str
    reasons: list[str]


class RiskEngine:
    def assess(self, evidence_items: list[Evidence]) -> RiskAssessment:
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

