from .models import DecisionProvenance
class DecisionRationale:
    def build(self,signal,priority):
        evidence=", ".join(signal.evidence_references) if signal.evidence_references else "No evidence references supplied"
        return f"Review {signal.category}. Why: observed {signal.direction} signal with {signal.severity} severity. Impact: governance attention may be required. Evidence: {evidence}. Confidence: {signal.confidence:.2f}. Priority rationale: advisory priority {priority}. Action: human review recommended."
