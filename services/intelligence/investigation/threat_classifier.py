"""
Sentinel DNA Threat Classifier

Classifies investigation activity
into attack categories.
"""

from __future__ import annotations

from typing import Any


class ThreatClassifier:
    """
    Classifies security threats.
    """

    def classify(
        self,
        alert: dict[str, Any],
        findings: dict[str, Any],
    ) -> dict[str, Any]:

        category = (
            alert.get("category")
            or ""
        ).lower()

        techniques = (
            findings
            .get("mitre", {})
            .get("techniques", [])
        )

        threat = "unknown"

        if (
            "phishing" in category
            or "T1566.002" in techniques
        ):
            threat = "credential_phishing"

        elif "malware" in category:
            threat = "malware"

        elif "login" in category:
            threat = "account_compromise"


        return {
            "classification": threat,
            "confidence": (
                0.9
                if threat != "unknown"
                else 0.3
            ),
        }