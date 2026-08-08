"""
Sentinel DNA Orchestration Result

Canonical result returned by an investigation workflow.

OrchestrationResult represents the aggregate outcome of an
ExecutionPlan.

It is intentionally separate from runtime ExecutionResult.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class OrchestrationResult:
    """
    Result returned after an investigation workflow executes.
    """

    plan_name: str

    success: bool = True

    agents_executed: list[str] = field(
        default_factory=list
    )

    results: dict[str, Any] = field(
        default_factory=dict
    )

    errors: list[str] = field(
        default_factory=list
    )

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


    # ------------------------------------------------------------------
    # Agent results
    # ------------------------------------------------------------------

    def add_agent_result(
        self,
        agent_name: str,
        result: Any,
    ) -> None:
        """
        Add a successful agent result.
        """

        if not agent_name:
            raise ValueError(
                "Agent name is required."
            )

        if agent_name not in self.agents_executed:
            self.agents_executed.append(
                agent_name
            )

        self.results[agent_name] = result


    # ------------------------------------------------------------------
    # Errors
    # ------------------------------------------------------------------

    def add_error(
        self,
        error: str,
    ) -> None:
        """
        Record an orchestration error.

        Any recorded orchestration error makes the aggregate
        result unsuccessful.
        """

        if not error:
            return

        self.errors.append(
            str(error)
        )

        self.success = False


    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        """
        Return a lightweight investigation summary.
        """

        return {
            "plan_name": self.plan_name,
            "success": self.success,
            "agents": list(
                self.agents_executed
            ),
            "errors": list(
                self.errors
            ),
            "result_count": len(
                self.results
            ),
        }


    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the complete orchestration result.
        """

        return {
            "plan_name": self.plan_name,
            "success": self.success,
            "agents_executed": list(
                self.agents_executed
            ),
            "results": dict(
                self.results
            ),
            "errors": list(
                self.errors
            ),
            "metadata": dict(
                self.metadata
            ),
        }