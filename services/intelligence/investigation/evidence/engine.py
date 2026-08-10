"""
Sentinel DNA Evidence Intelligence Engine.

Transforms raw investigation input into
structured intelligence evidence.

Responsibilities:

- Evidence normalization
- Artifact classification
- IOC extraction
- Evidence context generation
"""


import re

from typing import Any

from .models import (
    EvidenceArtifact,
    EvidenceCollection,
)



class EvidenceIntelligenceEngine:
    """
    Core evidence processing engine.
    """


    def normalize(
        self,
        case_id: str,
        evidence: Any,
    ) -> EvidenceCollection:
        """
        Normalize raw evidence into
        structured investigation artifacts.
        """

        artifacts = []


        normalized = self._normalize_input(
            evidence
        )


        for item in normalized:

            artifact = (
                self.classify_artifact(
                    item
                )
            )

            artifacts.append(
                artifact
            )


        return EvidenceCollection(

            case_id=case_id,

            artifacts=artifacts,

            metadata={
                "engine":
                    "evidence_intelligence",

                "artifact_count":
                    len(artifacts),
            },
        )



    def classify_artifact(
        self,
        artifact: Any,
    ) -> EvidenceArtifact:
        """
        Classify evidence artifact type.
        """

        source = "unknown"

        value = artifact


        if isinstance(
            artifact,
            dict,
        ):

            source = artifact.get(
                "source",
                "unknown",
            )

            value = artifact


        artifact_text = str(
            artifact
        ).lower()


        artifact_type = (
            "unknown_artifact"
        )


        if (
            "email" in artifact_text
            or "sender" in artifact_text
            or "subject" in artifact_text
        ):

            artifact_type = (
                "phishing_email"
            )


        elif (
            "url" in artifact_text
            or "http://" in artifact_text
            or "https://" in artifact_text
        ):

            artifact_type = (
                "malicious_url"
            )


        elif (
            "file" in artifact_text
            or "attachment" in artifact_text
            or ".exe" in artifact_text
        ):

            artifact_type = (
                "suspicious_file"
            )


        indicators = (
            self.extract_indicators(
                artifact
            )
        )


        risk = (
            self._calculate_risk(
                indicators,
                artifact_type,
            )
        )


        confidence = (
            self._calculate_confidence(
                indicators
            )
        )


        return EvidenceArtifact(

            artifact_type=artifact_type,

            value=value,

            source=source,

            risk=risk,

            confidence=confidence,

            indicators=indicators,

            metadata={
                "engine":
                    "evidence_classifier",
            },
        )



    def extract_indicators(
        self,
        evidence: Any,
    ) -> list[str]:
        """
        Extract potential IOC indicators.

        Detects:

        - URLs
        - Domains
        - IP addresses
        - Hash-like values
        """

        text = str(
            evidence
        )


        indicators = []


        urls = re.findall(
            r"https?://[^\s]+",
            text,
        )


        indicators.extend(
            urls
        )


        domains = re.findall(
            r"\b[a-zA-Z0-9.-]+\.(com|net|org|xyz|top|click|ru)\b",
            text,
        )


        for domain in domains:

            if domain not in indicators:

                indicators.append(
                    domain
                )


        ips = re.findall(
            r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            text,
        )


        indicators.extend(
            ips
        )


        hashes = re.findall(
            r"\b[a-fA-F0-9]{32,64}\b",
            text,
        )


        indicators.extend(
            hashes
        )


        return list(
            dict.fromkeys(
                indicators
            )
        )



    def build_evidence_context(
        self,
        collection: EvidenceCollection,
    ) -> dict:
        """
        Build AI reasoning context.
        """

        artifacts = (
            collection.artifacts
        )


        return {

            "case_id":
                collection.case_id,

            "artifact_count":
                len(artifacts),

            "risk_levels": [
                artifact.risk
                for artifact in artifacts
            ],

            "indicators": [

                indicator

                for artifact in artifacts

                for indicator
                in artifact.indicators

            ],

            "artifacts": [

                artifact.to_dict()

                for artifact in artifacts

            ],
        }



    def _normalize_input(
        self,
        evidence,
    ):

        if isinstance(
            evidence,
            list,
        ):

            return evidence


        return [
            evidence
        ]



    def _calculate_risk(
        self,
        indicators,
        artifact_type,
    ):

        if indicators:

            return "high"


        if artifact_type != "unknown_artifact":

            return "medium"


        return "low"



    def _calculate_confidence(
        self,
        indicators,
    ):

        if len(indicators) >= 3:

            return 90


        if len(indicators) == 2:

            return 75


        if len(indicators) == 1:

            return 60


        return 40