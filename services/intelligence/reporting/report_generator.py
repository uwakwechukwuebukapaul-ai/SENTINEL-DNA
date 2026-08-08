"""
Sentinel DNA AI Investigation Report Generator
"""

from __future__ import annotations

from typing import Any


from .executive_summary import (
    ExecutiveSummaryGenerator,
)

from .timeline_builder import (
    TimelineBuilder,
)



class ReportGenerator:
    """
    Builds complete investigation reports.
    """

    def __init__(self):

        self.summary_generator = (
            ExecutiveSummaryGenerator()
        )

        self.timeline_builder = (
            TimelineBuilder()
        )


    def generate(
        self,
        investigation: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate final SOC report.
        """

        report = {

            "case_id":
                investigation.get(
                    "case_id"
                ),

            "summary":
                self.summary_generator.generate(
                    investigation
                ),

            "timeline":
                self.timeline_builder.build(
                    investigation
                ),

            "status":
                investigation.get(
                    "status",
                    "unknown",
                ),
        }


        return report