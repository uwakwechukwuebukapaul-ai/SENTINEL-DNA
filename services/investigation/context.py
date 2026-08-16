"""Canonical investigation context for evidence-only enrichment."""
from dataclasses import dataclass, field
from typing import Any

@dataclass
class InvestigationContext:
    investigation_id: str
    tenant_id: str
    actor_id: str
    evidence: list[dict[str, Any]] = field(default_factory=list)

    def add_evidence(self, evidence: dict[str, Any], tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise PermissionError("evidence tenant does not match investigation tenant")
        self.evidence.append(dict(evidence))
