from enum import Enum
from dataclasses import dataclass, field
from typing import Any


class TaskStatus(Enum):

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"



@dataclass
class Task:

    capability: str
    payload: dict[str, Any]

    status: TaskStatus = TaskStatus.PENDING

    result: Any = None

    error: str | None = None