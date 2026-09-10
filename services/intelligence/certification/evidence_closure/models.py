"""Immutable models for final enterprise evidence closure."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceClosureReport:
    report_version: str
    generated_at: str
    commit_sha: str
    closure_result: str
    evidence_sources: tuple[dict[str, Any], ...]
    control_matrix: tuple[dict[str, Any], ...]
    total_controls: int
    passed_controls: tuple[str, ...]
    pending_controls: tuple[str, ...]
    failed_controls: tuple[str, ...]
    warnings: tuple[str, ...]
    remaining_blockers: tuple[str, ...]
    replay_digest_references: tuple[dict[str, str], ...]
    timestamp_metadata: dict[str, Any]
    provenance_metadata: dict[str, Any]
    replay_digest: str
    artifact_digest: str
    immutable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "commit_sha": self.commit_sha,
            "closure_result": self.closure_result,
            "evidence_sources": [dict(item) for item in self.evidence_sources],
            "control_matrix": [dict(item) for item in self.control_matrix],
            "total_controls": self.total_controls,
            "passed_controls": list(self.passed_controls),
            "pending_controls": list(self.pending_controls),
            "failed_controls": list(self.failed_controls),
            "warnings": list(self.warnings),
            "remaining_blockers": list(self.remaining_blockers),
            "replay_digest_references": [dict(item) for item in self.replay_digest_references],
            "timestamp_metadata": dict(self.timestamp_metadata),
            "provenance_metadata": dict(self.provenance_metadata),
            "replay_digest": self.replay_digest,
            "artifact_digest": self.artifact_digest,
            "immutable": self.immutable,
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, sort_keys=True, default=str) + "\n"


__all__ = ["EvidenceClosureReport"]
