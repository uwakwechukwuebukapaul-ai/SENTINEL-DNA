"""
Sentinel DNA Runtime Task Priority

Defines execution priority levels
for runtime scheduling.
"""

from enum import Enum


class TaskPriority(str, Enum):
    """
    Runtime task priority.

    Lower execution order value means
    higher scheduling priority.
    """

    CRITICAL = "critical"

    HIGH = "high"

    NORMAL = "normal"

    LOW = "low"