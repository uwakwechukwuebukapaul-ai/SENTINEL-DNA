"""
Sentinel DNA Investigation Coordinator

Coordinates:

- Investigation planning
- Runtime task execution
- Agent orchestration
- Investigation result generation

Enterprise orchestration layer between
AI agents and runtime execution.
"""

from dataclasses import dataclass, field

from .investigation_plan import InvestigationPlan


@dataclass
class InvestigationContext:
    """
    Investigation execution context.
    """

    investigation_id: str
    artifacts: list = field(default_factory=list)



class InvestigationResult:
    """
    Stable investigation result contract.
    """

    def __init__(
        self,
        case_id,
        plan,
        execution=None,
        status="completed",
    ):

        self.case_id = case_id

        self.plan = plan

        self.plan_name = (
            getattr(
                plan,
                "plan_name",
                getattr(
                    plan,
                    "name",
                    "Standard Security Investigation",
                ),
            )
        )

        self.execution = execution

        self.status = status

        self.results = []

        self.errors = []


        if execution is not None:

            self.results.append(
                execution
            )


            if isinstance(
                execution,
                dict,
            ):

                if execution.get("error"):

                    self.errors.append(
                        execution["error"]
                    )


    def to_dict(self):

        return {

            "case_id":
                self.case_id,

            "plan_name":
                self.plan_name,

            "status":
                self.status,

            "results":
                self.results,

            "errors":
                self.errors,

            "execution":
                self.execution,

        }



class InvestigationCoordinator:
    """
    Coordinates complete investigation lifecycle.
    """

    def __init__(
        self,
        registry=None,
        runtime=None,
    ):

        self.registry = registry

        self.runtime = runtime



    # --------------------------------------------------
    # Context creation
    # --------------------------------------------------

    def create_context(
        self,
        investigation_id,
        artifacts,
    ):
        """
        Create investigation context.
        """

        return InvestigationContext(

            investigation_id=investigation_id,

            artifacts=artifacts,

        )



    # --------------------------------------------------
    # Planning
    # --------------------------------------------------

    def create_plan(
        self,
        case_id,
        alert,
    ):

        return InvestigationPlan(

            case_id=case_id,

            name=(
                "Standard Security Investigation"
            ),

            plan_name=(
                "Standard Security Investigation"
            ),

            agents=[

                "investigation_execution",

                "threat_intelligence",

                "ioc_enrichment",

            ],

        )



    # --------------------------------------------------
    # Runtime task adapter
    # --------------------------------------------------

    def _create_runtime_task(
        self,
        case_id,
        alert,
        plan,
    ):

        class CompatibilityTask:

            def __init__(self):

                self.case_id = case_id

                self.alert = alert

                self.plan = plan

                self.capability = (
                    "investigation_execution"
                )

                self.status = "created"

                self.result = None

                self.error = None



            def start(self):

                self.status = "running"



            def complete(
                self,
                result=None,
            ):

                self.status = "completed"

                self.result = result



            def fail(
                self,
                error,
            ):

                self.status = "failed"

                self.error = error



        return CompatibilityTask()



    # --------------------------------------------------
    # Investigation execution
    # --------------------------------------------------

    def investigate(
        self,
        case_id,
        alert,
    ):

        alert = dict(alert)

        alert["case_id"] = case_id


        plan = self.create_plan(

            case_id,

            alert,

        )


        execution = {

            "case_id":
                case_id,

            "alert":
                alert,

            "status":
                "completed",

        }



        if self.runtime:

            task = self._create_runtime_task(

                case_id,

                alert,

                plan,

            )


            runtime_result = (
                self.runtime.execute(
                    task
                )
            )


            execution["runtime"] = runtime_result



        return InvestigationResult(

            case_id=case_id,

            plan=plan,

            execution=execution,

            status="completed",

        )