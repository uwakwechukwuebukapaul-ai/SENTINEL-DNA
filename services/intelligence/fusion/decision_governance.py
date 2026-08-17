"""Advisory governance for fused intelligence; never a decision engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


GOVERNANCE_POLICY_VERSION = "intelligence-governance-v1"
STATES = frozenset({"SUPPORTING", "CONTRADICTING", "INCONCLUSIVE", "NO_INTELLIGENCE", "STALE_INTELLIGENCE", "UNAVAILABLE", "INVALID_INTELLIGENCE"})


def _value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


@dataclass(frozen=True)
class IntelligenceGovernanceResult:
    policy_version: str
    state: str
    fusion_status: str
    confidence: float | None
    freshness: Mapping[str, Any]
    supporting_providers: tuple[str, ...]
    conflicting_providers: tuple[str, ...]
    stale_providers: tuple[str, ...]
    unavailable_providers: tuple[str, ...]
    provenance_references: tuple[Mapping[str, Any], ...]
    decision_influence: str
    reason: str
    timestamp: datetime
    tenant_id: str | None = None
    investigation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_version": self.policy_version, "state": self.state, "fusion_status": self.fusion_status,
            "confidence": self.confidence, "freshness": dict(self.freshness),
            "supporting_providers": list(self.supporting_providers), "conflicting_providers": list(self.conflicting_providers),
            "stale_providers": list(self.stale_providers), "unavailable_providers": list(self.unavailable_providers),
            "provenance_references": list(self.provenance_references), "decision_influence": self.decision_influence,
            "reason": self.reason, "timestamp": self.timestamp.isoformat(), "tenant_id": self.tenant_id,
            "investigation_id": self.investigation_id,
        }


class IntelligenceDecisionGovernance:
    """Classifies evidence into advisory states; it cannot mutate decisions."""

    def __init__(self, policy_version: str = GOVERNANCE_POLICY_VERSION):
        self.policy_version = policy_version

    def evaluate(self, fusion: Any, context: Any = None, timestamp: datetime | None = None) -> IntelligenceGovernanceResult:
        now = timestamp or datetime.now(timezone.utc)
        status = str(_value(fusion, "status", "")).upper()
        if not status:
            state, reason = "INVALID_INTELLIGENCE", "Fusion result has no status."
        elif status == "NO_INTELLIGENCE":
            state, reason = "NO_INTELLIGENCE", "No usable external intelligence was available."
        elif status == "CONFLICTED":
            state, reason = "CONTRADICTING", "Independent providers materially disagree."
        elif status in {"MALICIOUS", "BENIGN", "SUSPICIOUS"}:
            stale = tuple(_value(fusion, "stale_providers", ()) or ())
            state = "STALE_INTELLIGENCE" if stale else "SUPPORTING"
            reason = "Fused intelligence is advisory evidence; final decisions remain with canonical engines."
        elif status in {"UNAVAILABLE", "ERROR"}:
            state, reason = "UNAVAILABLE", "Provider intelligence was unavailable."
        else:
            state, reason = "INVALID_INTELLIGENCE", "Fusion status is unsupported."
        supporting = tuple(_value(fusion, "supporting_providers", ()) or ())
        conflicting = tuple(_value(fusion, "conflicting_providers", ()) or ())
        stale = tuple(_value(fusion, "stale_providers", ()) or ())
        unavailable = tuple(_value(fusion, "unavailable_providers", ()) or ())
        provenance = tuple(_value(fusion, "provenance", ()) or ())
        return IntelligenceGovernanceResult(
            self.policy_version, state, status or "UNKNOWN", _value(fusion, "aggregate_confidence"),
            {"stale_providers": list(stale)}, supporting, conflicting, stale, unavailable, provenance,
            "ADVISORY_ONLY", reason, now, _value(context, "tenant_id"), _value(context, "investigation_id"),
        )
