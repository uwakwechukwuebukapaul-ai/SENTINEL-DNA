"""
Sentinel DNA Autonomous Investigation Engine

Coordinates:

- Investigation state
- Investigation memory
- Pipeline execution
- Decision generation
- Autonomous workflow control
"""

from .investigation_state import (
    InvestigationState,
)

from .investigation_memory import (
    InvestigationMemory,
)



class AutonomousInvestigator:
    """
    Autonomous investigation controller.

    Orchestrates the full investigation lifecycle:

    Artifacts
        |
        v
    Pipeline
        |
        v
    Analysis
        |
        v
    Decision
        |
        v
    Memory
    """



    def __init__(
        self,
        pipeline=None,
        decision_engine=None,
        memory=None,
        state=None,
    ):

        self.pipeline = pipeline

        self.decision_engine = (
            decision_engine
        )

        self.memory = (
            memory
            or InvestigationMemory()
        )

        self.state = (
            state
            or InvestigationState()
        )



    def investigate(
        self,
        case_id: str,
        artifacts=None,
    ):
        """
        Execute autonomous investigation.

        Args:

            case_id:
                Investigation identifier

            artifacts:
                Evidence collected during investigation

        Returns:

            Investigation result dictionary
        """


        if artifacts is None:

            artifacts = []



        self.state.start()



        result = {

            "case_id":
                case_id,

            "artifacts":
                artifacts,

        }



        pipeline_result = {}



        if self.pipeline:


            if hasattr(
                self.pipeline,
                "execute",
            ):

                pipeline_result = (
                    self.pipeline.execute(
                        artifacts
                    )
                )


            elif hasattr(
                self.pipeline,
                "run",
            ):

                pipeline_result = (
                    self.pipeline.run(
                        artifacts
                    )
                )



        result[
            "pipeline"
        ] = pipeline_result



        #
        # Promote analysis output
        # to investigation root
        #

        if isinstance(
            pipeline_result,
            dict,
        ):


            if "analysis" in pipeline_result:

                result[
                    "analysis"
                ] = (
                    pipeline_result[
                        "analysis"
                    ]
                )



        #
        # Decision generation
        #

        decision_result = {}



        if self.decision_engine:


            if hasattr(
                self.decision_engine,
                "decide",
            ):

                decision_result = (
                    self.decision_engine.decide(
                        result
                    )
                )



        result[
            "decision"
        ] = decision_result



        self.state.complete()



        result[
            "status"
        ] = self.state.status



        self.memory.add(
            result
        )


        return result



    def get_history(
        self,
    ):

        return self.memory.get_history()



    def clear_history(
        self,
    ):

        self.memory.clear()