"""
Sentinel DNA Executive Summary Generator
"""

from __future__ import annotations

from typing import Any


class ExecutiveSummaryGenerator:
    """
    Generates analyst-friendly executive summaries.
    """

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def generate(
        self,
        investigation: dict[str, Any],
    ) -> str:
        """
        Generate executive summary text.
        """

        case_id = investigation.get(
            "case_id",
            "UNKNOWN",
        )

        severity = investigation.get(
            "severity",
            "unknown",
        )

        summary = (
            f"Case {case_id}: "
            f"{severity} security investigation completed."
        )

        self.history.append(
            {
                "case_id": case_id,
                "summary": summary,
            }
        )

        return summary

    def get_history(
        self,
    ) -> list[dict[str, Any]]:
        return self.history

    def clear_history(
        self,
    ) -> None:
        self.history.clear()