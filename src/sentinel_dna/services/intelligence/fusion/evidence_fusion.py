from typing import Any

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentinel_dna.investigation.context import InvestigationContext

from .models import (
    FusionEvidence,
    FusionResult,
)

from .scoring import (
    calculate_fusion_score,
    determine_verdict,
)



class EvidenceFusionEngine:
    """
    Sentinel DNA Evidence Fusion Engine.

    Combines:

    - Evidence Engine output
    - IOC intelligence
    - MITRE mappings
    - threat classification
    - risk signals

    into one intelligence layer.
    """


    def fuse(
        self,
        context: InvestigationContext,
    ) -> FusionResult:
        """
        Fuse investigation signals.
        """


        signals: list[dict[str, Any]] = []

        sources: list[str] = []


        for evidence in context.evidence_items:

            signal = {

                "source":
                    "evidence_engine",

                "category":
                    "evidence",

                "confidence":
                    getattr(
                        evidence,
                        "confidence",
                        0.0,
                    ),

                "severity":
                    getattr(
                        evidence,
                        "risk",
                        None,
                    ),

                "summary":
                    getattr(
                        evidence,
                        "summary",
                        "",
                    ),
            }


            signals.append(
                signal
            )

            sources.append(
                "evidence_engine"
            )



        for ioc, intelligence in (
            context.intelligence
            .get(
                "iocs",
                {},
            )
            .items()
        ):

            signals.append(
                {

                    "source":
                        "ioc_intelligence",

                    "category":
                        "ioc",

                    "indicator":
                        ioc,

                    "confidence":
                        (
                            0.8
                            if intelligence.get(
                                "reputation"
                            )
                            == "suspicious"
                            else
                            0.3
                        ),

                    "severity":
                        (
                            "high"
                            if intelligence.get(
                                "reputation"
                            )
                            == "suspicious"
                            else
                            "low"
                        ),

                }
            )

            sources.append(
                "ioc_intelligence"
            )



        for technique in context.mitre_attack:

            signals.append(
                {

                    "source":
                        "mitre_attack",

                    "category":
                        "technique",

                    "confidence":
                        0.7,

                    "severity":
                        "medium",

                    "technique":
                        technique.get(
                            "technique"
                        ),

                }
            )

            sources.append(
                "mitre_attack"
            )



        confidence = (
            calculate_fusion_score(
                signals
            )
        )


        verdict = determine_verdict(
            confidence,
            signals,
        )


        return FusionResult(

            confidence=confidence,

            verdict=verdict,

            contributing_sources=sorted(
                set(
                    sources
                )
            ),

            evidence_count=len(
                signals
            ),

            signals=signals,

            metadata={
                "engine":
                    "EvidenceFusionEngine",

                "version":
                    "1.0",
            },
        )