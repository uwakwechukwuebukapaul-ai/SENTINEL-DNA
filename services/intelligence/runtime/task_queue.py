"""
Sentinel DNA Runtime Task Queue

Enterprise workload queue.

Responsibilities:

- Store pending tasks
- Manage task ordering
- Retrieve executable workloads
- Protect queue state
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .task import Task


@dataclass
class TaskQueue:
    """
    Runtime task queue.
    """

    _tasks: list[Task] = field(
        default_factory=list
    )


    def enqueue(
        self,
        task: Task,
    ) -> None:
        """
        Add task to queue.
        """

        task.queue()

        self._tasks.append(
            task
        )


    def dequeue(
        self,
    ) -> Task | None:
        """
        Retrieve next task.
        """

        if not self._tasks:
            return None

        return self._tasks.pop(0)


    def peek(
        self,
    ) -> Task | None:
        """
        View next task.
        """

        if not self._tasks:
            return None

        return self._tasks[0]


    def tasks(
        self,
    ) -> list[Task]:
        """
        Return queued tasks.

        Returns copy to protect state.
        """

        return list(
            self._tasks
        )


    def size(
        self,
    ) -> int:
        """
        Return queue size.
        """

        return len(
            self._tasks
        )


    def empty(
        self,
    ) -> bool:
        """
        Check queue empty.
        """

        return not self._tasks


    def clear(
        self,
    ) -> None:
        """
        Remove all queued tasks.
        """

        self._tasks.clear()


    def status(
        self,
    ) -> dict:
        """
        Queue status.
        """

        return {
            "queued_tasks": len(
                self._tasks
            ),
            "tasks": [
                task.to_dict()
                for task in self._tasks
            ],
        }