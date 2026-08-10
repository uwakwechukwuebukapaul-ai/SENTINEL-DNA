"""
Sentinel DNA Investigation Pipeline Models.

Canonical typed contracts for the investigation intelligence pipeline.

The pipeline result intentionally supports both attribute-style and
dictionary-style access so newer typed consumers and legacy SOC/API
consumers can coexist safely.

Compatibility:

    result.status
    result.risk
    result.confidence

and:

    result["status"]
    result["risk"]
    result["confidence"]
    result["results"]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class InvestigationPipelineStage(str, Enum):
    """
    Supported investigation pipeline stages.
    """

    EVIDENCE = "evidence"
    IOC = "ioc"
    THREAT = "threat"
    GRAPH = "graph"
    TIMELINE = "timeline"
    INTEGRATION = "integration"


@dataclass
class InvestigationPipelineResult:
    """
    Canonical result contract for a Sentinel DNA investigation.

    Supports typed access:

        result.status
        result.risk
        result.confidence
        result.evidence
        result.iocs
        result.threats
        result.graph
        result.timeline
        result.integration

    and legacy mapping-style access:

        result["status"]
        result["risk"]
        result["confidence"]
        result["results"]

    ``results`` is exposed as a compatibility view containing the five
    core intelligence outputs:

        evidence
        iocs
        threats
        graph
        timeline

    Integration remains available separately because it represents the
    unified aggregation of those intelligence layers.
    """

    case_id: str

    status: str = "completed"

    evidence: Any = None

    iocs: Any = None

    threats: Any = None

    graph: Any = None

    timeline: Any = None

    integration: Any = None

    risk: str = "unknown"

    confidence: float = 0.0

    stages: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    # ------------------------------------------------------------------
    # Compatibility result collection
    # ------------------------------------------------------------------

    @property
    def results(self) -> list[Any]:
        """
        Return the five core intelligence pipeline results.

        This property intentionally excludes ``integration`` because
        integration is the aggregation layer over the five core
        intelligence outputs.

        The returned order is stable:

            1. evidence
            2. iocs
            3. threats
            4. graph
            5. timeline
        """

        return [
            self.evidence,
            self.iocs,
            self.threats,
            self.graph,
            self.timeline,
        ]

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert the typed result into a serializable dictionary.

        ``results`` is explicitly included for legacy consumers.
        """

        data = asdict(
            self
        )

        data["results"] = [
            self._serialize_result(
                item
            )
            for item in self.results
        ]

        return data

    @staticmethod
    def _serialize_result(
        value: Any,
    ) -> Any:
        """
        Serialize nested intelligence results when possible.
        """

        if value is None:
            return None

        if isinstance(
            value,
            dict,
        ):
            return {
                key:
                    InvestigationPipelineResult._serialize_result(
                        item
                    )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple),
        ):
            return [
                InvestigationPipelineResult._serialize_result(
                    item
                )
                for item in value
            ]

        if hasattr(
            value,
            "to_dict",
        ) and callable(
            value.to_dict
        ):
            try:
                return value.to_dict()
            except (
                TypeError,
                ValueError,
            ):
                pass

        return value

    # ------------------------------------------------------------------
    # Mapping compatibility
    # ------------------------------------------------------------------

    def __getitem__(
        self,
        key: str,
    ) -> Any:
        """
        Support dictionary-style access.

        Examples:

            result["status"]
            result["risk"]
            result["results"]
        """

        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "InvestigationPipelineResult keys must be strings"
            )

        if key == "results":
            return self.results

        try:
            return getattr(
                self,
                key,
            )
        except AttributeError as exc:
            raise KeyError(
                key
            ) from exc

    def get(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Dictionary-compatible get().
        """

        if not isinstance(
            key,
            str,
        ):
            raise TypeError(
                "InvestigationPipelineResult keys must be strings"
            )

        if key == "results":
            return self.results

        return getattr(
            self,
            key,
            default,
        )

    def keys(self):
        """
        Return available result keys.

        Includes the legacy ``results`` compatibility key.
        """

        keys = list(
            self.to_dict().keys()
        )

        return dict.fromkeys(
            keys
        ).keys()

    def values(self):
        """
        Return result values.
        """

        return [
            self[key]
            for key in self.keys()
        ]

    def items(self):
        """
        Return result key/value pairs.
        """

        return [
            (
                key,
                self[key],
            )
            for key in self.keys()
        ]

    def __contains__(
        self,
        key: object,
    ) -> bool:
        """
        Support:

            "status" in result
            "results" in result
        """

        if not isinstance(
            key,
            str,
        ):
            return False

        if key == "results":
            return True

        return hasattr(
            self,
            key,
        )

    def __iter__(self):
        """
        Iterate over result keys for mapping compatibility.
        """

        return iter(
            self.keys()
        )

    def __len__(
        self,
    ) -> int:
        """
        Return the number of exposed mapping fields.
        """

        return len(
            list(
                self.keys()
            )
        )

    def __repr__(
        self,
    ) -> str:
        """
        Provide a useful enterprise debugging representation.
        """

        return (
            "InvestigationPipelineResult("
            f"case_id={self.case_id!r}, "
            f"status={self.status!r}, "
            f"risk={self.risk!r}, "
            f"confidence={self.confidence!r}, "
            f"stages={self.stages!r}"
            ")"
        )