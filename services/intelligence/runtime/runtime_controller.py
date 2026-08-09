"""
Sentinel DNA Runtime Controller

Enterprise runtime control plane.

Responsible for:

- runtime lifecycle
- task submission
- execution control
- health reporting
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .task import Task
from .execution_result import ExecutionResult
from .runtime_execution_manager import RuntimeExecutionManager


@dataclass
class RuntimeController:
    """
    High-level runtime controller.

    Provides a stable API boundary between
    runtime clients and execution infrastructure.
    """

    manager: RuntimeExecutionManager = field(
        default_factory=RuntimeExecutionManager
    )

    initialized: bool = False


    # =====================================================
    # Lifecycle
    # =====================================================

    def initialize(
        self,
    ) -> None:
        """
        Initialize runtime.
        """

        self.manager.start()

        self.initialized = True



    def shutdown(
        self,
    ) -> None:
        """
        Shutdown runtime.
        """

        self.manager.stop()

        self.initialized = False



    # =====================================================
    # Submission
    # =====================================================

    def submit(
        self,
        task: Task,
    ):
        """
        Submit runtime task.
        """

        return self.manager.submit(
            task
        )



    # =====================================================
    # Registration
    # =====================================================

    def register(
        self,
        capability: str,
        handler,
    ) -> bool:
        """
        Register runtime capability.
        """

        return self.manager.register_handler(
            capability,
            handler,
        )



    # =====================================================
    # Execution
    # =====================================================

    def execute(
        self,
        task: Task,
    ) -> ExecutionResult:
        """
        Execute runtime task.

        Normalizes every execution response into
        ExecutionResult.
        """

        try:

            capability = getattr(
                task,
                "capability",
                None,
            )


            payload = getattr(
                task,
                "payload",
                None,
            )


            if capability is None:

                return ExecutionResult.failure(
                    error="Task missing capability."
                )


            result = self.manager.execute(
                capability,
                payload,
            )


            if isinstance(
                result,
                ExecutionResult,
            ):

                return result



            if result is None:

                return ExecutionResult.failure(
                    error="Execution returned no result."
                )



            return ExecutionResult.success(
                output=result,
                data=result,
            )


        except Exception as exc:

            return ExecutionResult.failure(
                error=str(exc)
            )



    # =====================================================
    # Status
    # =====================================================

    def status(
        self,
    ) -> dict[str, Any]:
        """
        Runtime snapshot.
        """

        return {

            "initialized":
                self.initialized,

            "runtime":
                self.manager.status(),

        }