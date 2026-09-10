"""Immutable enterprise readiness certification models."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CertificationEvidence:
    evidence_id: str
    source: str
    source_report_version: str
    status: str
    source_report_digest: str
    source_replay_digest: str
    evidence_digest: str
    references: tuple[str, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationControl:
    control_id: str
    domain: str
    name: str
    required: bool
    passed: bool
    evidence_ids: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationMetric:
    metric_id: str
    domain: str
    name: str
    value: float
    unit: str
    evidence_ids: tuple[str, ...]
    interpretation: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationFinding:
    finding_id: str
    severity: str
    status: str
    title: str
    description: str
    evidence_ids: tuple[str, ...]
    remediation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CertificationReport:
    report_version: str
    timestamp: str
    environment_metadata: dict[str, Any]
    commit_sha: str
    validation_digest: str
    evidence: tuple[CertificationEvidence, ...]
    controls: tuple[CertificationControl, ...]
    metrics: tuple[CertificationMetric, ...]
    findings: tuple[CertificationFinding, ...]
    passed_controls: tuple[str, ...]
    failed_controls: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_references: tuple[str, ...]
    replay_digest: str
    report_digest: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "timestamp": self.timestamp,
            "environment_metadata": self.environment_metadata,
            "commit_sha": self.commit_sha,
            "validation_digest": self.validation_digest,
            "evidence": [item.to_dict() for item in self.evidence],
            "controls": [item.to_dict() for item in self.controls],
            "metrics": [item.to_dict() for item in self.metrics],
            "findings": [item.to_dict() for item in self.findings],
            "passed_controls": list(self.passed_controls),
            "failed_controls": list(self.failed_controls),
            "warnings": list(self.warnings),
            "evidence_references": list(self.evidence_references),
            "replay_digest": self.replay_digest,
            "report_digest": self.report_digest,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str) + "\n"


__all__ = [
    "CertificationControl",
    "CertificationEvidence",
    "CertificationFinding",
    "CertificationMetric",
    "CertificationReport",
]
