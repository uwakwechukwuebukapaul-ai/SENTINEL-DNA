"""
Sentinel DNA IOC Intelligence Engine.

Responsibilities:

- IOC classification
- Reputation enrichment
- Risk scoring
- MITRE ATT&CK mapping
- Threat context generation
"""


import re

from typing import Any

from .models import (
    IOCRecord,
    IOCCollection,
)



class IOCIntelligenceEngine:
    """
    Enriches indicators extracted from investigations.
    """


    def enrich(
        self,
        case_id: str,
        indicators: list[Any],
    ) -> IOCCollection:
        """
        Enrich a list of indicators.
        """

        records = []


        for indicator in indicators:

            record = self.classify(
                indicator
            )

            records.append(
                record
            )


        return IOCCollection(

            case_id=case_id,

            indicators=records,

            metadata={

                "engine":
                    "ioc_intelligence",

                "indicator_count":
                    len(records),
            },
        )



    def classify(
        self,
        indicator: Any,
    ) -> IOCRecord:
        """
        Classify and enrich IOC.
        """

        value = str(
            indicator
        ).strip()


        indicator_type = (
            self._detect_type(
                value
            )
        )


        reputation = (
            self._reputation_lookup(
                value,
                indicator_type,
            )
        )


        risk = (
            self.calculate_risk(
                value,
                reputation,
            )
        )


        confidence = (
            self._confidence(
                indicator_type,
                reputation,
            )
        )


        mitre = (
            self.map_mitre(
                indicator_type
            )
        )


        return IOCRecord(

            indicator=value,

            indicator_type=indicator_type,

            risk=risk,

            confidence=confidence,

            reputation=reputation,

            mitre_techniques=mitre,

            sources=[

                "sentinel_dna_ioc_engine"

            ],

            context={

                "classification":
                    indicator_type,

                "analysis":
                    "automated IOC enrichment",

            },
        )



    def calculate_risk(
        self,
        indicator: str,
        reputation: str,
    ) -> str:
        """
        Calculate indicator risk.
        """

        value = indicator.lower()


        suspicious_patterns = [

            ".xyz",

            ".top",

            ".click",

            ".ru",

            "login",

            "verify",

            "secure",

            "update",

        ]


        if reputation == "malicious":

            return "critical"


        for pattern in suspicious_patterns:

            if pattern in value:

                return "high"


        return "low"



    def map_mitre(
        self,
        indicator_type: str,
    ) -> list[str]:
        """
        Map IOC category to MITRE ATT&CK.
        """

        mappings = {

            "url": [
                "T1566.002"
            ],

            "domain": [
                "T1566.002"
            ],

            "ip_address": [
                "T1071"
            ],

            "hash": [
                "T1204"
            ],

        }


        return mappings.get(
            indicator_type,
            [],
        )



    def build_context(
        self,
        collection: IOCCollection,
    ) -> dict:
        """
        Build investigation context.
        """

        return {

            "case_id":
                collection.case_id,

            "indicator_count":
                len(collection.indicators),

            "high_risk_indicators": [

                record.indicator

                for record
                in collection.indicators

                if record.risk
                in [
                    "high",
                    "critical",
                ]

            ],

            "mitre": [

                technique

                for record
                in collection.indicators

                for technique
                in record.mitre_techniques

            ],

            "indicators": [

                record.to_dict()

                for record
                in collection.indicators

            ],
        }



    def _detect_type(
        self,
        indicator: str,
    ) -> str:

        if re.match(
            r"^https?://",
            indicator,
        ):

            return "url"


        if re.match(
            r"^\d{1,3}(\.\d{1,3}){3}$",
            indicator,
        ):

            return "ip_address"


        if re.match(
            r"^[a-fA-F0-9]{32,64}$",
            indicator,
        ):

            return "hash"


        if "." in indicator:

            return "domain"


        return "unknown"



    def _reputation_lookup(
        self,
        indicator: str,
        indicator_type: str,
    ) -> str:
        """
        Offline reputation simulation.

        Designed for future integration with:

        - VirusTotal
        - AbuseIPDB
        - MISP
        - OpenCTI
        """

        suspicious = [

            ".xyz",

            ".top",

            ".click",

            "evil",

            "malware",

        ]


        value = indicator.lower()


        for item in suspicious:

            if item in value:

                return "malicious"


        return "unknown"



    def _confidence(
        self,
        indicator_type: str,
        reputation: str,
    ) -> int:

        if reputation == "malicious":

            return 90


        if indicator_type != "unknown":

            return 70


        return 40