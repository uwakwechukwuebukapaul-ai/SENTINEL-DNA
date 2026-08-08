"""
Sentinel DNA Runtime Scheduler

Priority based task scheduler for
the Intelligence Runtime Framework.

Responsibilities:

- Queue runtime tasks
- Maintain execution ordering
- Handle task lifecycle transitions
- Provide task retrieval/removal APIs
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .task import Task
from .task_status import TaskStatus
from .task_priority import TaskPriority


@dataclass
class Scheduler:
    """
    Controls task scheduling lifecycle.
    """

    tasks: list[Task] = field(
        default_factory=list
    )


    def schedule(
        self,
        task: Task,
    ) -> None:
        """
        Add task into scheduler.

        Highest priority tasks are
        returned first.
        """

        task.queue()

        self.tasks.append(task)

        self._sort_tasks()


    def _sort_tasks(self) -> None:
        """
        Sort tasks by enterprise priority order.
        """

        priority_order = {
            TaskPriority.CRITICAL: 0,
            TaskPriority.HIGH: 1,
            TaskPriority.NORMAL: 2,
            TaskPriority.LOW: 3,
        }

        self.tasks.sort(
            key=lambda item:
                priority_order.get(
                    item.priority,
                    99,
                )
        )


    def next_task(
        self,
    ) -> Task | None:
        """
        Return highest priority queued task.
        """

        if not self.tasks:
            return None

        return self.tasks.pop(0)


    def remove(
        self,
        task_id: str,
    ) -> bool:
        """
        Remove task by id.
        """

        for task in self.tasks:

            if task.task_id == task_id:

                self.tasks.remove(task)

                return True

        return False


    def clear(
        self,
    ) -> None:
        """
        Remove all scheduled tasks.
        """

        self.tasks.clear()


    def size(
        self,
    ) -> int:
        """
        Return queued task count.
        """

        return len(self.tasks)


    def contains(
        self,
        task_id: str,
    ) -> bool:
        """
        Check task existence.
        """

        return any(
            task.task_id == task_id
            for task in self.tasks
        )


    def pending_tasks(
        self,
    ) -> list[Task]:
        """
        Return current queued tasks.
        """

        return list(self.tasks)