"""Enterprise trust-closure report models."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class TrustClosureFinding:
    finding_id: str
    category: str
    severity: str
    status: str
    title: str
    description: str
    evidence_references: tuple[str, ...]
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrustClosureReport:
    report_version: str
    timestamp: str
    commit_sha: str
    previous_certification: dict[str, Any]
    security_hardening: dict[str, bool]
    release_evidence_hygiene: dict[str, bool]
    deployment_readiness: dict[str, bool]
    findings: tuple[TrustClosureFinding, ...]
    remaining_risks: tuple[str, ...]
    production_blockers: tuple[str, ...]
    recommended_release_gates: tuple[str, ...]
    evidence_references: tuple[str, ...]
    replay_digest: str
    report_digest: str
    production_ready: bool
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "timestamp": self.timestamp,
            "commit_sha": self.commit_sha,
            "previous_certification": self.previous_certification,
            "security_hardening": self.security_hardening,
            "release_evidence_hygiene": self.release_evidence_hygiene,
            "deployment_readiness": self.deployment_readiness,
            "findings": [item.to_dict() for item in self.findings],
            "remaining_risks": list(self.remaining_risks),
            "production_blockers": list(self.production_blockers),
            "recommended_release_gates": list(self.recommended_release_gates),
            "evidence_references": list(self.evidence_references),
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
            "production_ready": self.production_ready,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str) + "\n"


__all__ = ["TrustClosureFinding", "TrustClosureReport"]
