"""
Sentinel DNA MITRE ATT&CK Adapter
"""

from __future__ import annotations


class MITREAdapter:
    """
    Maps investigation findings to ATT&CK techniques.
    """


    def execute(
        self,
        case_id: str,
        alert: dict,
    ) -> dict:

        techniques = []

        if alert.get("source") == "email":
            techniques.append(
                "T1566.002"
            )


        return {
            "case_id": case_id,
            "techniques": techniques,
        }