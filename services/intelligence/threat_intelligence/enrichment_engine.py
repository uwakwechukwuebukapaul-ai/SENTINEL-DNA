"""
Sentinel DNA - Threat Enrichment Engine

Provides intelligence context for
investigation workflows.
"""

from __future__ import annotations

from typing import Any


from .ioc_extractor import IOCExtractor



class EnrichmentEngine:
    """
    Enriches security events with
    threat intelligence context.
    """



    def __init__(
        self,
        extractor: IOCExtractor | None = None,
    ):

        self.extractor = (
            extractor
            or IOCExtractor()
        )



    def enrich(
        self,
        event: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate threat intelligence
        context.
        """


        indicators = (
            self.extractor.extract(
                event
            )
        )


        enriched = []


        for indicator in indicators:

            enriched.append(

                {

                    **indicator,

                    "reputation":
                        self._reputation(
                            indicator["value"]
                        ),

                    "confidence":
                        self._confidence(
                            indicator["type"]
                        ),

                    "risk":
                        self._risk(
                            indicator["value"]
                        ),

                    "attack_patterns":
                        self._attack_mapping(
                            indicator["type"]
                        ),

                }

            )


        return {

            "source":
                event.get(
                    "source",
                    "unknown",
                ),

            "case_id":
                event.get(
                    "case_id",
                    "UNKNOWN",
                ),

            "indicators":
                enriched,

            "risk_score":
                self._calculate_score(
                    enriched
                ),

        }



    def _reputation(
        self,
        value: str,
    ) -> str:

        suspicious_terms = [

            "malicious",

            "evil",

            "bad",

            "phish",

        ]


        value = value.lower()


        if any(
            term in value
            for term in suspicious_terms
        ):

            return "malicious"


        return "unknown"



    def _confidence(
        self,
        ioc_type: str,
    ) -> int:

        confidence = {

            "hash": 95,

            "ip": 85,

            "domain": 80,

            "url": 75,

        }


        return confidence.get(
            ioc_type,
            50,
        )



    def _risk(
        self,
        value: str,
    ) -> str:

        reputation = (
            self._reputation(value)
        )


        if reputation == "malicious":

            return "critical"


        return "low"



    def _attack_mapping(
        self,
        ioc_type: str,
    ) -> list[str]:

        mapping = {

            "domain":
                ["T1583"],

            "url":
                ["T1566"],

            "ip":
                ["T1071"],

            "hash":
                ["T1204"],

        }


        return mapping.get(
            ioc_type,
            [],
        )



    def _calculate_score(
        self,
        indicators,
    ) -> int:

        score = 0


        for indicator in indicators:

            if indicator["risk"] == "critical":

                score += 90

            else:

                score += 20


        return score