"""
Sentinel DNA Execution Plan Model

Defines autonomous investigation tasks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class InvestigationTask:
    """
    Single investigation execution task.
    """

    task_id: str

    agent: str

    action: str

    priority: str = "normal"

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


@dataclass
class ExecutionPlan:
    """
    Complete autonomous investigation plan.
    """

    case_id: str

    strategy: str

    tasks: list[InvestigationTask] = field(
        default_factory=list
    )


    def add_task(
        self,
        task: InvestigationTask,
    ) -> None:
        """
        Add execution task.
        """

        self.tasks.append(task)


    def to_dict(
        self,
    ) -> dict[str, Any]:
        """
        Serialize execution plan.
        """

        return {

            "case_id": self.case_id,

            "strategy": self.strategy,

            "tasks": [

                {
                    "task_id": task.task_id,
                    "agent": task.agent,
                    "action": task.action,
                    "priority": task.priority,
                    "metadata": task.metadata,
                }

                for task in self.tasks

            ],
        }