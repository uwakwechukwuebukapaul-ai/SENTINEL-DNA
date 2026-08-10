"""
Sentinel DNA MITRE ATT&CK Mapper.

Maps threat intelligence findings
to adversary techniques.
"""

from __future__ import annotations

from typing import Any


class MITREMapper:
    """
    Maps intelligence indicators
    to MITRE ATT&CK techniques.
    """

    TECHNIQUES = {
        "phishing": {
            "technique_id": "T1566",
            "name": "Phishing",
            "tactic": "Initial Access",
        },

        "credential": {
            "technique_id": "T1056",
            "name": "Input Capture",
            "tactic": "Collection",
        },

        "malware": {
            "technique_id": "T1204",
            "name": "User Execution",
            "tactic": "Execution",
        },

        "command": {
            "technique_id": "T1059",
            "name": "Command and Scripting Interpreter",
            "tactic": "Execution",
        },

        "exfiltration": {
            "technique_id": "T1041",
            "name": "Exfiltration Over C2 Channel",
            "tactic": "Exfiltration",
        },
    }


    def map(
        self,
        intelligence: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Map intelligence findings
        to ATT&CK techniques.
        """

        intelligence = intelligence or {}

        text = str(
            intelligence
        ).lower()


        matches = []


        for keyword, technique in self.TECHNIQUES.items():

            if keyword in text:

                matches.append(
                    {
                        **technique,

                        "confidence":
                            0.85,

                        "evidence":
                            [
                                keyword
                            ],
                    }
                )


        return matches


    def map_indicator(
        self,
        indicator: dict[str, Any],
    ) -> dict[str, Any]:

        """
        Map single indicator.
        """

        value = str(
            indicator.get(
                "value",
                ""
            )
        ).lower()


        result = self.map(
            {
                "indicator":
                    value
            }
        )


        if result:
            return result[0]


        return {
            "technique_id":
                None,

            "name":
                "Unknown",

            "tactic":
                "Unknown",

            "confidence":
                0.0,

            "evidence":
                [],
        }