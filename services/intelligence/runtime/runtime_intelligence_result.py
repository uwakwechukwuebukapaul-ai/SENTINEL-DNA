"""
Runtime Intelligence Result

Unified output model for Sentinel DNA
runtime intelligence execution.
"""

from dataclasses import dataclass, field
from typing import Any



@dataclass
class RuntimeIntelligenceResult:
    """
    Final runtime intelligence execution result.
    """


    success: bool


    risk: str = "unknown"


    confidence: float = 0.0


    mitre: list[str] = field(
        default_factory=list
    )


    providers: list[str] = field(
        default_factory=list
    )


    correlations: list[Any] = field(
        default_factory=list
    )


    intelligence_records: list[Any] = field(
        default_factory=list
    )


    fusion_results: list[Any] = field(
        default_factory=list
    )


    recommendations: list[str] = field(
        default_factory=list
    )


    metadata: dict[str, Any] = field(
        default_factory=dict
    )



    def add_metadata(
        self,
        key: str,
        value: Any,
    ):

        self.metadata[key] = value



    def to_dict(
        self,
    ):

        return {

            "success":
                self.success,


            "risk":
                self.risk,


            "confidence":
                self.confidence,


            "mitre":
                self.mitre,


            "providers":
                self.providers,


            "correlations":
                [

                    item.to_dict()
                    if hasattr(
                        item,
                        "to_dict"
                    )
                    else item

                    for item in self.correlations

                ],


            "intelligence_records":
                [

                    item.to_dict()
                    if hasattr(
                        item,
                        "to_dict"
                    )
                    else item

                    for item in self.intelligence_records

                ],


            "fusion_results":
                [

                    item.to_dict()
                    if hasattr(
                        item,
                        "to_dict"
                    )
                    else item

                    for item in self.fusion_results

                ],


            "recommendations":
                self.recommendations,


            "metadata":
                self.metadata,

        }



    def is_high_risk(
        self,
    ) -> bool:

        return self.risk.lower() in (
            "high",
            "critical",
        )