"""
Sentinel DNA Correlation Result

Unified correlation response contract.

Supports:

- Object access:
    result.risk

- Dictionary compatibility:
    result["risk"]

- API serialization:
    result.to_dict()
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CorrelationResult:
    """
    Standard correlation engine output.

    Shared by:

    - Correlation Engine
    - Threat Correlator
    - Investigation Intelligence
    - Fusion Layer
    - API responses
    """

    # Core result

    matched: bool = False

    risk: str = "unknown"

    confidence: float = 0.0


    # Intelligence entities

    entities: list[Any] = field(
        default_factory=list
    )

    relationships: list[Any] = field(
        default_factory=list
    )


    # Threat classification

    attack_pattern: str | None = None

    mitre: list[str] = field(
        default_factory=list
    )


    # Entity context

    entity_type: str | None = None

    value: str | None = None


    # Correlation metadata

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    # Investigation correlation

    case_id: str | None = None


    # Investigation compatibility

    indicators: list[Any] = field(
        default_factory=list
    )

    techniques: list[Any] = field(
        default_factory=list
    )

    attack_story: str | None = None


    # State

    status: str = "completed"


    # =====================================================
    # Dictionary Compatibility
    # =====================================================

    def __getitem__(
        self,
        key: str,
    ):
        """
        Allow:

            result["risk"]
        """

        return self.to_dict()[key]


    def get(
        self,
        key: str,
        default=None,
    ):
        """
        Dictionary-style get().
        """

        return self.to_dict().get(
            key,
            default,
        )


    # =====================================================
    # Serialization
    # =====================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Convert result into API-safe dictionary.
        """

        return {

            "matched":
                self.matched,


            "risk":
                self.risk,


            "confidence":
                self.confidence,


            "entities":
                self.entities,


            "relationships":
                self.relationships,


            "attack_pattern":
                self.attack_pattern,


            "mitre":
                self.mitre,


            "entity_type":
                self.entity_type,


            "value":
                self.value,


            "metadata":
                dict(
                    self.metadata
                ),


            "case_id":
                self.case_id,


            "indicators":
                self.indicators,


            "techniques":
                self.techniques,


            "attack_story":
                self.attack_story,


            "status":
                self.status,

        }


    # =====================================================
    # Runtime Helpers
    # =====================================================

    def update_metadata(
        self,
        values: dict[str, Any] | None = None,
        **kwargs,
    ):
        """
        Add metadata values.
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


    def __bool__(
        self,
    ):
        """
        Truth value follows match state.
        """

        return self.matched