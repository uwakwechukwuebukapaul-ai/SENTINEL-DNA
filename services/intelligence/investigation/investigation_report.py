"""
Sentinel DNA Investigation Report

Analyst-facing investigation report.
"""

from __future__ import annotations

from typing import Any


class InvestigationReport:
    """
    Converts investigation results
    into analyst format.
    """


    def __init__(
        self,
        case_id: str,
    ) -> None:

        self.case_id = case_id

        self.summary = ""

        self.findings: dict[str, Any] = {}

        self.timeline = []

        self.recommendations = []


    def build_from_result(
        self,
        result,
    ):

        data = (
            result.to_dict()
            if hasattr(
                result,
                "to_dict"
            )
            else result
        )


        self.findings = data.get(
            "findings",
            {}
        )

        self.timeline = data.get(
            "timeline",
            []
        )

        self.recommendations = data.get(
            "recommendations",
            []
        )

        self.summary = (
            "AI investigation completed"
        )


        return self


    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "summary":
                self.summary,

            "findings":
                self.findings,

            "timeline":
                self.timeline,

            "recommendations":
                self.recommendations,

        }