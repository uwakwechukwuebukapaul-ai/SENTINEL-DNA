"""
Investigation execution models.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TaskExecutionResult:
    """
    Result of executing one task.
    """

    task_name: str
    status: str
    output: dict = field(
        default_factory=dict
    )


@dataclass
class InvestigationResult:
    """
    Complete investigation execution result.
    """

    case_id: str
    status: str = "completed"

    results: List[TaskExecutionResult] = field(
        default_factory=list
    )


    def add_result(
        self,
        result: TaskExecutionResult,
    ):
        self.results.append(result)


    def to_dict(self):
        return {
            "case_id": self.case_id,
            "status": self.status,
            "results": [
                {
                    "task_name": item.task_name,
                    "status": item.status,
                    "output": item.output,
                }
                for item in self.results
            ],
        }