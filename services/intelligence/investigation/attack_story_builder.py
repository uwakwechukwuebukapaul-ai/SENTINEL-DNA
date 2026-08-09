"""
Sentinel DNA Attack Story Builder

Transforms investigation intelligence
into analyst-readable attack narratives.
"""

from __future__ import annotations

from typing import Any


class AttackStoryBuilder:
    """
    Builds attack narratives from investigation output.
    """

    def build(
        self,
        findings: dict[str, Any],
        graph: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        iocs = findings.get(
            "ioc",
            {},
        )

        mitre = findings.get(
            "mitre",
            {},
        )

        techniques = mitre.get(
            "techniques",
            [],
        )

        ioc_count = iocs.get(
            "ioc_count",
            0,
        )


        attack_path = []


        if ioc_count:

            attack_path.append(
                "Suspicious indicator detected"
            )


        if techniques:

            attack_path.append(
                "Attack technique identified"
            )


        if "T1566" in techniques:

            attack_path.append(
                "Phishing delivery observed"
            )


        if "T1078" in techniques:

            attack_path.append(
                "Possible credential abuse detected"
            )


        summary = (
            "Potential malicious activity detected"
            if attack_path
            else
            "No significant attack activity identified"
        )


        return {

            "summary": summary,

            "attack_path": attack_path,

            "ioc_count": ioc_count,

            "mitre_techniques": techniques,

            "graph": graph or {},

        }