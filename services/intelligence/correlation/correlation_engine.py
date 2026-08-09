"""
Sentinel DNA Intelligence Correlation Engine.

Combines:
- IOC intelligence
- MITRE mappings
- reasoning results

into investigation intelligence.
"""

from __future__ import annotations

from typing import Any

from .models import CorrelationResult

from .attack_chain import AttackChainBuilder



class CorrelationEngine:


    def __init__(
        self,
        attack_chain_builder=None,
    ):

        self.attack_chain_builder = (
            attack_chain_builder
            or AttackChainBuilder()
        )



    def correlate(
        self,
        case_id: str,
        indicators: list[dict[str, Any]],
        techniques: list[dict[str, Any]],
        reasoning: dict[str, Any] | None = None,
    ) -> CorrelationResult:


        confidence = 0.0


        if indicators:
            confidence += 0.4


        if techniques:
            confidence += 0.4


        if reasoning:
            confidence += 0.2



        story = (
            self.attack_chain_builder.build(
                indicators,
                techniques,
            )
        )


        normalized_confidence = round(
            min(
                confidence,
                1.0,
            ),
            2,
        )


        return CorrelationResult(

            case_id=case_id,

            indicators=indicators,

            techniques=techniques,

            attack_story=story,

            confidence=normalized_confidence,

            metadata={
                "engine":
                    "sentinel-dna-correlation",

                "reasoning_available":
                    reasoning is not None,
            },
        )