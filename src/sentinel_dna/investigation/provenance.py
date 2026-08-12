"""
Sentinel DNA Investigation Provenance Layer.

Tracks the origin and justification of
investigation decisions.

Purpose:

- evidence lineage
- AI reasoning transparency
- decision auditability
- compliance support
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ProvenanceRecord:
    """
    Single provenance event.
    """

    stage: str
    action: str
    source: str

    details: dict[str, Any] = field(
        default_factory=dict
    )

    confidence: float | None = None

    timestamp: str = field(
        default_factory=lambda:
            datetime.now(
                timezone.utc
            ).isoformat()
    )

    record_id: str = field(
        default_factory=lambda:
            str(uuid4())
    )


@dataclass
class InvestigationProvenance:
    """
    Complete investigation decision lineage.
    """

    case_id: str

    records: list[ProvenanceRecord] = field(
        default_factory=list
    )


    def add(
        self,
        stage: str,
        action: str,
        source: str,
        details: dict[str, Any] | None = None,
        confidence: float | None = None,
    ) -> None:
        self.records.append(
            ProvenanceRecord(
                stage=stage,
                action=action,
                source=source,
                details=details or {},
                confidence=confidence,
            )
        )


    def timeline(
        self,
    ) -> list[dict[str, Any]]:
        return [
            asdict(record)
            for record in self.records
        ]


    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "records": self.timeline(),
        }