"""
Sentinel DNA Agent Result Collector

Aggregates investigation findings.
"""

from __future__ import annotations

from typing import Any



class AgentResultCollector:
    """
    Collects agent execution results.
    """

    def __init__(self) -> None:

        self.results: list[
            dict[str, Any]
        ] = []



    def add_result(
        self,
        agent: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store agent result.
        """

        entry = {
            "agent": agent,
            "result": result,
        }


        self.results.append(
            entry
        )


        return entry



    def get_results(
        self,
    ) -> list[dict[str, Any]]:
        """
        Return collected results.
        """

        return self.results



    def clear(
        self,
    ) -> None:
        """
        Clear results.
        """

        self.results.clear()