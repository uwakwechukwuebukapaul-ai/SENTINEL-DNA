"""
Sentinel DNA Executive Summary Generator
"""

from __future__ import annotations

from typing import Any


class ExecutiveSummaryGenerator:
    """
    Generates analyst-facing investigation summaries.
    """

    def generate(
        self,
        investigation: dict[str, Any],
    ) -> str:

        case_id = investigation.get(
            "case_id",
            "UNKNOWN",
        )

        status = investigation.get(
            "status",
            "unknown",
        )

        result_count = len(
            investigation.get(
                "results",
                [],
            )
        )

        return (
            f"Investigation {case_id} "
            f"completed with status {status}. "
            f"Collected {result_count} "
            "intelligence results."
        )