import json
import re
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
        evidence_path = self._evidence_path(evidence.evidence_id)
        evidence_path.write_text(json.dumps(asdict(evidence), indent=2), encoding="utf-8")

    def get(self, evidence_id: str) -> Evidence:
        evidence_path = self._evidence_path(evidence_id)
        return Evidence(**json.loads(evidence_path.read_text(encoding="utf-8")))

    def get_for_tenant(self, evidence_id: str, tenant_id: str) -> Evidence:
        evidence = self.get(evidence_id)
        if evidence.tenant_id != tenant_id:
            raise PermissionError("evidence is not available in this tenant")
        return evidence

    def _extract_indicators(self, text: str) -> list[str]:
        indicators = []
        for token in text.replace("\n", " ").split():
            cleaned = token.strip(".,;:()[]{}<>\"'")
            if "@" in cleaned and "." in cleaned:
                indicators.append(cleaned)
            elif cleaned.lower().startswith(("http://", "https://")):
                indicators.append(cleaned)
        return sorted(set(indicators))

    def _evidence_path(self, evidence_id: str) -> Path:
        if not isinstance(evidence_id, str) or not re.fullmatch(r"ev-[A-Za-z0-9]{12}", evidence_id):
            raise ValueError("evidence_id is invalid")
        return self.evidence_dir / f"{evidence_id}.json"
