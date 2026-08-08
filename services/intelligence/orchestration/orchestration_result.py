"""
Sentinel DNA Orchestration Result

Standard output contract for
investigation execution.
"""

from __future__ import annotations

from typing import Any


class OrchestrationResult:


    def __init__(
        self,
        plan_name: str,
        success: bool = True,
    ):

        self.plan_name = plan_name

        self.success = success

        self.results: dict[
            str,
            Any
        ] = {}

        self.errors: list[str] = []

        self.agents_executed: list[str] = []

        self.metadata = {}



    def add_agent_result(
        self,
        agent_name: str,
        result: Any,
    ):

        self.results[
            agent_name
        ] = result



    def add_error(
        self,
        error: str,
    ):

        self.errors.append(
            error
        )

        self.success = False



    def add_metadata(
        self,
        key: str,
        value: Any,
    ):

        self.metadata[key] = value