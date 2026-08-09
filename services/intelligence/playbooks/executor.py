"""
Sentinel DNA SOAR Playbook Executor.

Executes security response workflows.
"""

from typing import Any

from .audit import PlaybookAudit



class PlaybookExecutor:


    def __init__(
        self,
        connectors=None,
        audit=None,
    ):


        self.connectors = (
            connectors
            or {}
        )


        self.audit = (
            audit
            or PlaybookAudit()
        )



    def execute(
        self,
        playbook,
        context: dict[str, Any],
    ):


        results = []


        for step in playbook.steps:


            if step.requires_approval:

                result = {

                    "status":
                        "approval_required",

                    "step":
                        step.name,

                }


            else:

                connector = (
                    self.connectors.get(
                        step.connector
                    )
                )


                if connector:

                    result = connector.execute(
                        step.action,
                        step.parameters,
                    )

                else:

                    result = {

                        "status":
                            "failed",

                        "reason":
                            "connector_not_found",

                    }



            event = {

                "playbook":
                    playbook.name,

                "step":
                    step.name,

                "result":
                    result,

            }


            self.audit.record(
                event
            )


            results.append(
                result
            )


        return {

            "status":
                "completed",

            "playbook":
                playbook.name,

            "results":
                results,

        }