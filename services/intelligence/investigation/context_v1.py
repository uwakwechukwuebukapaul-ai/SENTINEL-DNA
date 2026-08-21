"""Canonical InvestigationContext V1 and consumer projections.

The coordinator owns this state.  Downstream consumers receive a projection
so agent, reasoning, and Copilot code cannot establish competing context
schemas or accidentally mutate coordinator state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _ioc_projection(value: Any) -> dict[str, Any]:
    """Normalize one IOC at the projection boundary without losing metadata."""
    raw = value.to_dict() if hasattr(value, "to_dict") else value
    if isinstance(raw, dict):
        item = dict(raw)
    else:
        item = {"value": raw}
    item["ioc_id"] = str(item.get("ioc_id") or item.get("id") or "")
    item["ioc_type"] = str(item.get("ioc_type") or item.get("type") or "unknown")
    item["value"] = str(item.get("value") or item.get("indicator") or "")
    provenance = item.get("provenance") or item.get("source") or {}
    item["provenance"] = dict(provenance) if isinstance(provenance, dict) else {"source": str(provenance)}
    return item


@dataclass
class InvestigationContextV1:
    """The single coordinator-owned investigation context contract."""

    investigation_id: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    iocs: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    tenant_id: str | None = None
    actor_id: str | None = None
    correlation_id: str | None = None
    intelligence_provenance: dict[str, Any] = field(default_factory=dict)
    intelligence_evidence: list[dict[str, Any]] = field(default_factory=list)
    _queried_intelligence: list[tuple[str, str, str]] = field(default_factory=list, repr=False)

    def add_evidence(self, evidence: dict[str, Any], tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise PermissionError("evidence tenant does not match investigation tenant")
        item = dict(evidence)
        self.intelligence_evidence.append(item)
        self.evidence.append(dict(item))

    def to_dict(self) -> dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "case_id": self.investigation_id,
            "artifacts": [dict(item) for item in self.artifacts],
            "evidence": [dict(item) for item in self.evidence],
            "iocs": [_ioc_projection(item) for item in self.iocs],
            "timeline": [dict(item) for item in self.timeline],
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "intelligence_provenance": dict(self.intelligence_provenance),
        }

    snapshot = to_dict

    def agent_projection(self) -> dict[str, Any]:
        """Return the execution-safe view supplied to agents."""
        return {
            "investigation_id": self.investigation_id,
            "case_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "artifacts": [dict(item) for item in self.artifacts],
            "evidence": [dict(item) for item in self.evidence],
            "iocs": [_ioc_projection(item) for item in self.iocs],
            "timeline": [dict(item) for item in self.timeline],
        }

    def reasoning_projection(self) -> dict[str, Any]:
        """Return only evidence, IOCs, timeline, and trusted provenance."""
        return {
            "investigation_id": self.investigation_id,
            "case_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "evidence": [dict(item) for item in self.evidence],
            "iocs": [_ioc_projection(item) for item in self.iocs],
            "timeline": [dict(item) for item in self.timeline],
            "intelligence_provenance": dict(self.intelligence_provenance),
        }

    def copilot_projection(self, **sources: Any) -> dict[str, Any]:
        """Return the analyst-facing Copilot view, derived from V1 state."""
        projection = self.reasoning_projection()
        projection.update({key: value for key, value in sources.items() if value is not None})
        return projection

    def report_projection(self, result: Any) -> dict[str, Any]:
        """Expose only approved context and canonical result data to reporting."""
        data = result.to_dict() if hasattr(result, "to_dict") else dict(result or {})
        return {
            "case_id": self.investigation_id,
            "tenant_id": self.tenant_id,
            "actor_id": self.actor_id,
            "correlation_id": self.correlation_id,
            "evidence": [dict(item) for item in self.evidence],
            "iocs": [_ioc_projection(item) for item in self.iocs],
            "timeline": [dict(item) for item in self.timeline],
            "result": data,
        }
