import json
from dataclasses import asdict
from pathlib import Path

from sentinel_dna.evidence.models import Evidence


class EvidenceEngine:
    def __init__(self, data_dir: str | Path = "data") -> None:
        self.data_dir = Path(data_dir)
        self.evidence_dir = self.data_dir / "evidence"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)

    def normalize_email(self, email: dict) -> Evidence:
        subject = str(email.get("subject", "No subject"))
        sender = str(email.get("sender", "unknown sender"))
        body = str(email.get("body", ""))
        indicators = self._extract_indicators(f"{subject} {sender} {body}")
        suspicious_terms = ["urgent", "password", "verify", "invoice", "wire", "mfa", "login"]
        matches = [term for term in suspicious_terms if term in f"{subject} {body}".lower()]
        confidence = min(0.95, 0.35 + (0.12 * len(matches)) + (0.05 * len(indicators)))
        return Evidence(
            source="gmail",
            evidence_type="email",
            summary=f"Email from {sender}: {subject}",
            raw=email,
            confidence=round(confidence, 2),
            indicators=indicators,
        )

    def save(self, evidence: Evidence) -> None:
        evidence_path = self.evidence_dir / f"{evidence.evidence_id}.json"
        evidence_path.write_text(json.dumps(asdict(evidence), indent=2), encoding="utf-8")

    def get(self, evidence_id: str) -> Evidence:
        evidence_path = self.evidence_dir / f"{evidence_id}.json"
        return Evidence(**json.loads(evidence_path.read_text(encoding="utf-8")))

    def _extract_indicators(self, text: str) -> list[str]:
        indicators = []
        for token in text.replace("\n", " ").split():
            cleaned = token.strip(".,;:()[]{}<>\"'")
            if "@" in cleaned and "." in cleaned:
                indicators.append(cleaned)
            elif cleaned.lower().startswith(("http://", "https://")):
                indicators.append(cleaned)
        return sorted(set(indicators))

