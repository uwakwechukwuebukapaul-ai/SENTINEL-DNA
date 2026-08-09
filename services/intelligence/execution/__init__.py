"""
Sentinel DNA Intelligence Execution Layer

Responsible for converting investigation
decisions into executable SOC actions.
"""

from .execution_engine import (
    ExecutionEngine,
    ExecutionResult,
)


__all__ = [
    "ExecutionEngine",
    "ExecutionResult",
]