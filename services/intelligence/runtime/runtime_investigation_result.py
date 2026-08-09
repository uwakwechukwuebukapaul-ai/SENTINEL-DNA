"""
Runtime Investigation Result

Final output model for investigation execution.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuntimeInvestigationResult:

    success: bool

    investigation_id: str

    risk: str = "unknown"

    confidence: float = 0.0

    intelligence: Any = None

    decisions: list[Any] = field(
        default_factory=list
    )

    timeline: list[dict[str, Any]] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    def to_dict(
        self,
    ):

        return {

            "success":
                self.success,

            "investigation_id":
                self.investigation_id,

            "risk":
                self.risk,

            "confidence":
                self.confidence,

            "intelligence":
                (
                    self.intelligence.to_dict()
                    if hasattr(
                        self.intelligence,
                        "to_dict",
                    )
                    else self.intelligence
                ),

            "decisions":
                self.decisions,

            "timeline":
                self.timeline,

            "metadata":
                self.metadata,

        }