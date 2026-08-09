"""
Sentinel DNA Intelligence Correlation Engine

Correlates investigation signals.
"""

from __future__ import annotations

from typing import Any


class CorrelationEngine:

    def correlate(
        self,
        alert: dict[str, Any],
        findings: dict[str, Any],
    ) -> dict[str, Any]:

        correlation = {

            "ioc_count":
                findings
                .get("ioc", {})
                .get(
                    "ioc_count",
                    0
                ),

            "mitre_techniques":
                findings
                .get("mitre", {})
                .get(
                    "techniques",
                    []
                ),

            "alert_category":
                alert.get(
                    "category"
                ),

        }


        correlation["risk_signal"] = (
            "high"
            if (
                correlation["ioc_count"]
                and correlation["mitre_techniques"]
            )
            else
            "normal"
        )


        return correlation