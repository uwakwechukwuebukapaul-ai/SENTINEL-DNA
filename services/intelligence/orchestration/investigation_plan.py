"""
Sentinel DNA Investigation Plan

Defines autonomous investigation execution plans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(init=False)
class InvestigationPlan:
    """
    Defines an investigation workflow.

    Supports:

    Legacy fields:
    - case_id
    - name
    - stages

    Current fields:
    - investigation_id
    - plan_name
    - steps
    """

    investigation_id: str | None

    plan_name: str

    agents: list[str]

    steps: list[Any]

    metadata: dict[str, Any]


    def __init__(
        self,
        investigation_id: str | None = None,
        plan_name: str | None = None,
        agents: list[str] | None = None,
        steps: list[Any] | None = None,
        metadata: dict[str, Any] | None = None,
        case_id: str | None = None,
        name: str | None = None,
        stages: list[Any] | None = None,
    ):
        """
        Initialize investigation plan.

        Maintains backward compatibility
        across Sentinel DNA orchestration versions.
        """

        self.investigation_id = (
            investigation_id
            or case_id
        )

        self.plan_name = (
            plan_name
            or name
            or "Standard Security Investigation"
        )

        self.agents = (
            list(agents)
            if agents
            else []
        )

        self.steps = (
            list(steps)
            if steps
            else []
        )

        if stages:
            self.steps.extend(
                stages
            )

        self.metadata = (
            dict(metadata)
            if metadata
            else {}
        )


    # --------------------------------------------------
    # Agent Management
    # --------------------------------------------------

    def add_agent(
        self,
        agent_name: str,
    ) -> None:
        """
        Add agent to investigation workflow.
        """

        if not agent_name:
            return

        if agent_name not in self.agents:
            self.agents.append(
                agent_name
            )


    # --------------------------------------------------
    # Step Management
    # --------------------------------------------------

    def add_step(
        self,
        step: Any,
    ) -> None:
        """
        Add execution step.
        """

        if step is None:
            return

        self.steps.append(
            step
        )


    # --------------------------------------------------
    # Stage Compatibility
    # --------------------------------------------------

    def add_stage(
        self,
        stage: str,
    ) -> None:
        """
        Legacy alias for add_step().
        """

        self.add_step(
            stage
        )


    @property
    def stages(
        self,
    ) -> list[Any]:
        """
        Legacy stages accessor.

        Older orchestration tests and modules
        reference stages instead of steps.
        """

        return self.steps


    # --------------------------------------------------
    # Legacy Properties
    # --------------------------------------------------

    @property
    def case_id(
        self,
    ) -> str | None:
        return self.investigation_id


    @property
    def name(
        self,
    ) -> str:
        return self.plan_name


    # --------------------------------------------------
    # Serialization
    # --------------------------------------------------

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "investigation_id": self.investigation_id,
            "case_id": self.case_id,
            "plan_name": self.plan_name,
            "name": self.name,
            "agents": list(
                self.agents
            ),
            "steps": list(
                self.steps
            ),
            "stages": list(
                self.stages
            ),
            "metadata": dict(
                self.metadata
            ),
        }


    def __repr__(
        self,
    ) -> str:

        return (
            "InvestigationPlan("
            f"id={self.investigation_id!r}, "
            f"name={self.plan_name!r}, "
            f"agents={self.agents!r}, "
            f"steps={self.steps!r}"
            ")"
        )