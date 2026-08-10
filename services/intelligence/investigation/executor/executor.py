"""
Sentinel DNA Investigation Executor.

Executes investigation plans.
"""


from ...models import (
    InvestigationResult,
    TaskExecutionResult,
)

from ..evidence.collector import (
    EvidenceCollector,
)


class InvestigationExecutor:
    """
    Executes investigation plans.
    """


    def __init__(self):

        self.evidence_collector = (
            EvidenceCollector()
        )


    def execute(
        self,
        plan,
    ) -> InvestigationResult:
        """
        Execute investigation workflow.
        """

        result = InvestigationResult(
            case_id=plan.case_id
        )


        for task in plan.tasks:

            evidence = (
                self.evidence_collector.collect(
                    task
                )
            )


            task.status = "completed"


            execution = TaskExecutionResult(
                task_name=task.name,
                status="completed",
                output={
                    "evidence": [
                        item.to_dict()
                        for item in evidence
                    ]
                },
            )


            result.add_result(
                execution
            )


        return result