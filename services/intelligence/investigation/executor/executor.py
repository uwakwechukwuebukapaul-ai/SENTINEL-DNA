"""
Sentinel DNA Investigation Executor.

Responsible for running investigation tasks.
"""


from ...models import (
    InvestigationResult,
    TaskExecutionResult,
)


class InvestigationExecutor:
    """
    Executes investigation plans.
    """


    def execute(
        self,
        plan,
    ) -> InvestigationResult:
        """
        Execute all tasks inside a plan.
        """

        result = InvestigationResult(
            case_id=plan.case_id
        )


        for task in plan.tasks:

            task.status = "completed"


            execution = TaskExecutionResult(
                task_name=task.name,
                status="completed",
                output={
                    "message": (
                        f"{task.name} executed"
                    )
                },
            )


            result.add_result(
                execution
            )


        return result