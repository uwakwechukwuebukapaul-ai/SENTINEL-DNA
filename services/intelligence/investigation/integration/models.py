"""
Sentinel DNA Investigation Intelligence Integration Models.

Defines the stable data contract used to combine individual
investigation intelligence outputs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class InvestigationIntegrationResult:
    """
    Unified investigation intelligence result.

    This model keeps the outputs of the individual intelligence
    engines together without tightly coupling those engines.
    """

    case_id: str

    evidence: list[Any] = field(
        default_factory=list
    )

    iocs: list[Any] = field(
        default_factory=list
    )

    threats: list[Any] = field(
        default_factory=list
    )

    graph: Any = None

    timeline: Any = None

    risk: str = "low"

    confidence: int = 50

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the result into a serializable dictionary.
        """

        return {
            "case_id": self.case_id,
            "evidence": self._serialize(
                self.evidence
            ),
            "iocs": self._serialize(
                self.iocs
            ),
            "threats": self._serialize(
                self.threats
            ),
            "graph": self._serialize(
                self.graph
            ),
            "timeline": self._serialize(
                self.timeline
            ),
            "risk": self.risk,
            "confidence": self.confidence,
            "metadata": dict(
                self.metadata
            ),
        }

    @classmethod
    def _serialize(
        cls,
        value: Any,
    ) -> Any:
        """
        Recursively serialize common Sentinel DNA objects.
        """

        if value is None:
            return None

        if isinstance(
            value,
            list,
        ):
            return [
                cls._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            tuple,
        ):
            return [
                cls._serialize(item)
                for item in value
            ]

        if isinstance(
            value,
            dict,
        ):
            return {
                key: cls._serialize(item)
                for key, item in value.items()
            }

        to_dict = getattr(
            value,
            "to_dict",
            None,
        )

        if callable(to_dict):
            return cls._serialize(
                to_dict()
            )

        if hasattr(
            value,
            "__dataclass_fields__",
        ):
            return cls._serialize(
                asdict(value)
            )

        return value