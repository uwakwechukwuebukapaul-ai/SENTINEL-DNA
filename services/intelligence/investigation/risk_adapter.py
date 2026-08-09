"""
Sentinel DNA Risk Adapter

Transforms intelligence findings
into analyst risk verdicts.
"""

from __future__ import annotations

from typing import Any


class RiskAdapter:

    def calculate(
        self,
        alert: dict[str, Any],
        findings: dict[str, Any],
    ) -> dict[str, Any]:

        score = 0
        reasons = []


        ioc_data = findings.get(
            "ioc",
            {}
        )

        ioc_count = ioc_data.get(
            "ioc_count",
            0
        )


        if ioc_count:
            score += 30
            reasons.append(
                "Suspicious indicators detected"
            )


        mitre = findings.get(
            "mitre",
            {}
        )


        techniques = mitre.get(
            "techniques",
            []
        )


        if "T1566.002" in techniques:

            score += 50

            reasons.append(
                "Credential phishing technique detected"
            )


        if alert.get(
            "severity"
        ) == "HIGH":

            score += 20

            reasons.append(
                "High severity alert"
            )


        if score >= 80:
            severity = "critical"

        elif score >= 60:
            severity = "high"

        elif score >= 30:
            severity = "medium"

        else:
            severity = "low"


        return {
            "score": score,
            "severity": severity,
            "confidence": min(
                score / 100,
                0.99
            ),
            "reasons": reasons,
        }