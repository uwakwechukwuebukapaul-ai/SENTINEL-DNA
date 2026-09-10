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
        text = str(alert or {}).lower()

        if "powershell" in text or "pwsh" in text:
            techniques.append("T1059.001")

        if alert.get("source") == "email":
            techniques.append(
                "T1566.002"
            )


        return {
            "case_id": case_id,
            "techniques": techniques,
        }
