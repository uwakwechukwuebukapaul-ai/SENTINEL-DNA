"""Evidence contract for operational ownership, without inventing owners."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "sentinel-dna-operational-ownership-evidence.v1"
REPLAY_VERSION = "sentinel-dna-operational-ownership-replay.v1"
REQUIRED_EVIDENCE = (
    "security_ownership_assignment",
    "incident_escalation_ownership",
    "platform_ownership",
    "database_ownership",
    "release_approval_ownership",
    "operational_review_responsibility",
)


def _digest(value: Any) -> str:
    return hashlib.sha256((json.dumps(value, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode("utf-8")).hexdigest()


class OperationalOwnershipEvidenceValidator:
    """Validate an operator-supplied evidence index; default is pending."""

    def __init__(
        self,
        *,
        repository_root: str | Path,
        evidence_path: str | Path | None = None,
        documentation_path: str | Path | None = None,
        generated_at: str | None = None,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.evidence_path = Path(evidence_path).resolve() if evidence_path else None
        self.documentation_path = Path(documentation_path).resolve() if documentation_path else self.repository_root / "docs" / "OPERATIONAL_OWNERSHIP_EVIDENCE.md"
        self.generated_at = str(generated_at or datetime.now(timezone.utc).isoformat())

    def run(self) -> dict[str, Any]:
        evidence: dict[str, Any] = {}
        parse_error = None
        if self.evidence_path is not None:
            try:
                payload = json.loads(self.evidence_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    evidence = payload
                else:
                    parse_error = "invalid_evidence_shape"
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                parse_error = "evidence_unavailable_or_invalid"
        documentation_present = self.documentation_path.is_file() and not self.documentation_path.is_symlink()
        checks = {name: bool(evidence.get(name)) for name in REQUIRED_EVIDENCE}
        checks["no_production_owner_invented"] = True
        checks["ownership_documentation_present"] = documentation_present
        checks["evidence_is_local_and_bounded"] = documentation_present and parse_error is None
        blockers = []
        if self.evidence_path is None:
            blockers.append("OPERATIONAL-OWNERSHIP:evidence_index_not_supplied")
        if parse_error:
            blockers.append(f"OPERATIONAL-OWNERSHIP:{parse_error}")
        if not documentation_present:
            blockers.append("OPERATIONAL-OWNERSHIP:documentation_not_supplied")
        blockers.extend(f"OPERATIONAL-OWNERSHIP:{name}" for name, passed in checks.items() if not passed)
        pending = [name for name in REQUIRED_EVIDENCE if not checks[name]]
        evidence_missing = self.evidence_path is None or bool(pending) or not documentation_present
        result = "passed" if all(checks.values()) else ("blocked" if evidence_missing else "failed")
        bounded = {
            "evidence_path_supplied": self.evidence_path is not None,
            "evidence_file_name": self.evidence_path.name if self.evidence_path else None,
            "documentation_file_name": self.documentation_path.name,
            "documentation_present": documentation_present,
            "owner_values_serialized": False,
            "required_evidence_names": list(REQUIRED_EVIDENCE),
            "pending_evidence": pending,
        }
        stable = {
            "replay_version": REPLAY_VERSION,
            "checks": checks,
            "blockers": sorted(set(blockers)),
            "pending_evidence": pending,
            "evidence_file_present": bounded["evidence_path_supplied"],
            "documentation_present": documentation_present,
        }
        replay = _digest(stable)
        body = {
            "report_version": REPORT_VERSION,
            "generated_at": self.generated_at,
            "validation_result": result,
            "checks": checks,
            "pending_checks": pending,
            "blockers": sorted(set(blockers)),
            "warnings": ["no production owner or on-call identity is inferred", "ownership evidence requires real assignment outside this repository"],
            "evidence": bounded,
            "replay_digest": replay,
        }
        return {**body, "report_digest": _digest(body)}


__all__ = ["OperationalOwnershipEvidenceValidator", "REQUIRED_EVIDENCE"]
