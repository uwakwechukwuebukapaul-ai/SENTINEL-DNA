from sentinel_dna.evidence.evidence_engine import EvidenceEngine
from sentinel_dna.evidence.models import Evidence


class GmailAnalyzer:
    def __init__(self, evidence_engine: EvidenceEngine | None = None) -> None:
        self.evidence_engine = evidence_engine or EvidenceEngine()

    def analyze_message(self, message: dict) -> Evidence:
        evidence = self.evidence_engine.normalize_email(message)
        self.evidence_engine.save(evidence)
        return evidence

