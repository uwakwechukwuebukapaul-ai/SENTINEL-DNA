"""
Sentinel DNA Investigation Result

Unified investigation response contract.

Used by:

- Investigation Orchestrator
- Investigation Pipeline
- Investigation Service
- Execution Orchestrator
- Runtime Intelligence
- SOC Dashboard
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InvestigationResult:
    """
    Standard AI investigation output contract.
    """

    # =====================================================
    # Identity
    # =====================================================

    investigation_id: Optional[str] = None

    case_id: Optional[str] = None


    # =====================================================
    # State
    # =====================================================

    status: str = "pending"

    message: Optional[str] = None


    # =====================================================
    # Intelligence Outputs
    # =====================================================

    correlation: Any = None

    fusion: Any = None

    reasoning: Any = None


    # =====================================================
    # Findings
    # =====================================================

    findings: list[Any] = field(
        default_factory=list
    )

    indicators: list[Any] = field(
        default_factory=list
    )

    entities: list[Any] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )


    # =====================================================
    # Threat Assessment
    # =====================================================

    risk_level: str = "unknown"

    risk_score: int = 0

    confidence: float = 0.0


    # =====================================================
    # Response Intelligence
    # =====================================================

    mitre: list[str] = field(
        default_factory=list
    )

    recommendations: list[str] = field(
        default_factory=list
    )


    # =====================================================
    # Metadata
    # =====================================================

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    created_at: Optional[str] = None



    # =====================================================
    # Metadata Compatibility
    # =====================================================

    def add_metadata(
        self,
        key: str,
        value: Any,
    ):
        """
        Add single metadata value.
        """

        self.metadata[key] = value

        return self



    def update_metadata(
        self,
        values: Optional[dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Update metadata values.

        Compatible with:
        - Investigation Pipeline
        - Investigation Service
        - Runtime consumers
        """

        if values:
            self.metadata.update(
                values
            )

        if kwargs:
            self.metadata.update(
                kwargs
            )

        return self



    # =====================================================
    # Serialization
    # =====================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "status":
                self.status,

            "message":
                self.message,

            "correlation":
                self.correlation,

            "fusion":
                self.fusion,

            "reasoning":
                self.reasoning,

            "findings":
                self.findings,

            "indicators":
                self.indicators,

            "entities":
                self.entities,

            "relationships":
                self.relationships,

            "risk":

                {
                    "level":
                        self.risk_level,

                    "score":
                        self.risk_score,

                    "confidence":
                        self.confidence,
                },


            "mitre":
                self.mitre,

            "recommendations":
                self.recommendations,

            "metadata":
                dict(
                    self.metadata
                ),

            "created_at":
                self.created_at,
        }



    # =====================================================
    # Dictionary Compatibility
    # =====================================================

    def __getitem__(
        self,
        key: str,
    ):
        return self.to_dict()[key]



    def get(
        self,
        key: str,
        default=None,
    ):
        return self.to_dict().get(
            key,
            default,
        )



    # =====================================================
    # Status Helpers
    # =====================================================

    @property
    def completed(
        self,
    ) -> bool:

        return self.status == "completed"



    @property
    def failed(
        self,
    ) -> bool:

        return self.status == "failed"



    def __bool__(
        self,
    ):

        return self.completed



    # =====================================================
    # Factories
    # =====================================================

    @classmethod
    def success(
        cls,
        **kwargs,
    ):

        kwargs.setdefault(
            "status",
            "completed",
        )

        return cls(
            **kwargs
        )



    @classmethod
    def failure(
        cls,
        error: str,
        **kwargs,
    ):

        kwargs.setdefault(
            "status",
            "failed",
        )

        kwargs.setdefault(
            "message",
            error,
        )

        return cls(
            **kwargs
        )