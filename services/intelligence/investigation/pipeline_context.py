"""
Sentinel DNA Investigation Pipeline Context
"""

from __future__ import annotations

from typing import Any



class InvestigationPipelineContext:
    """
    Shared state during investigation execution.
    """

    def __init__(
        self,
        case_id: str,
        alert: dict[str, Any],
    ) -> None:

        self.case_id = case_id
        self.alert = alert

        self.results: list[
            dict[str, Any]
        ] = []


        self.status = "initialized"



    def add_result(
        self,
        result: dict[str, Any],
    ) -> None:

        self.results.append(
            result
        )



    def complete(
        self,
    ) -> None:

        self.status = "completed"



    def failed(
        self,
    ) -> None:

        self.status = "failed"



    def export(
        self,
    ) -> dict[str, Any]:

        return {
            "case_id": self.case_id,
            "alert": self.alert,
            "status": self.status,
            "results": self.results,
        }