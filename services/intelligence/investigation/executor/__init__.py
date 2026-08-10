"""
Sentinel DNA Investigation Executor.

Executes investigation plans
created by the planner layer.
"""

from ...models import (
    InvestigationResult,
    TaskExecutionResult,
)

__all__ = [
    "InvestigationResult",
    "TaskExecutionResult",
]