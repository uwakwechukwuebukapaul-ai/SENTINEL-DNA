"""
Investigation Planner Data Models.

Defines the core objects used by
Sentinel DNA investigation planning.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class InvestigationTask:
    """
    Represents a single investigation action.
    """

    name: str
    priority: str = "medium"
    status: str = "pending"
    description: str = ""

    def complete(self):
        """
        Mark task as completed.
        """
        self.status = "completed"


@dataclass
class InvestigationPlan:
    """
    Represents a complete investigation strategy.
    """

    case_id: str
    objective: str
    tasks: List[InvestigationTask] = field(
        default_factory=list
    )

    metadata: dict = field(
        default_factory=dict
    )

    def add_task(
        self,
        task: InvestigationTask,
    ):
        """
        Add investigation task.
        """

        self.tasks.append(task)


    def task_count(self) -> int:
        """
        Return number of planned tasks.
        """

        return len(self.tasks)


    def to_dict(self) -> dict:
        """
        Serialize investigation plan.
        """

        return {
            "case_id": self.case_id,
            "objective": self.objective,
            "metadata": self.metadata,
            "task_count": self.task_count(),
            "tasks": [
                {
                    "name": task.name,
                    "priority": task.priority,
                    "status": task.status,
                    "description": task.description,
                }
                for task in self.tasks
            ],
        }