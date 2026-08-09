"""
Sentinel DNA Investigation Executor

Backward compatible investigation execution layer.
"""

from __future__ import annotations

from datetime import datetime, UTC



class InvestigationExecutor:
    """
    Executes investigation plans.

    Supports:
    - Agent dispatcher execution
    - Intelligence pipeline execution
    """

    def __init__(
        self,
        executor=None,
    ) -> None:

        self.executor = executor

        self.history = []


    def execute(
        self,
        plan,
        context,
    ):

        started = datetime.now(
            UTC
        )

        result = None


        #
        # Pipeline execution
        #

        if hasattr(
            self.executor,
            "execute"
        ):

            try:

                result = self.executor.execute(
                    plan,
                    context,
                )

            except TypeError:

                result = self.executor.execute(
                    plan.get(
                        "case_id"
                    ),
                    context,
                )


        #
        # Agent dispatcher execution
        #

        elif hasattr(
            self.executor,
            "dispatch"
        ):

            findings = []


            for task in plan.get(
                "tasks",
                []
            ):

                output = (
                    self.executor.dispatch(
                        task["name"],
                        context,
                    )
                )

                findings.append(
                    output
                )


            result = {

                "case_id":
                    plan.get(
                        "case_id"
                    ),

                "status":
                    "completed",

                "findings":
                    findings,

            }


        else:

            result = {

                "case_id":
                    plan.get(
                        "case_id"
                    ),

                "status":
                    "completed",

                "findings":
                    [],

            }



        if hasattr(
            result,
            "to_dict"
        ):

            result = result.to_dict()



        execution = {

            "status":
                "completed",

            "findings":
                result.get(
                    "findings",
                    []
                ),

            "result":
                result,

            "duration_seconds":
                (
                    datetime.now(
                        UTC
                    )
                    -
                    started
                ).total_seconds(),

        }


        self.history.append(
            execution
        )


        return execution



    def get_history(self):

        return self.history



    def clear_history(self):

        self.history.clear()