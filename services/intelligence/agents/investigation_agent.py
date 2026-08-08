"""
Sentinel DNA Investigation Agent

Enterprise autonomous investigation planning
and execution agent.
"""

from __future__ import annotations


from services.intelligence.agents.base_agent import (
    BaseAgent,
)

from services.intelligence.agents.agent_capability import (
    AgentCapability,
)

from services.intelligence.agents.agent_context import (
    AgentContext,
)

from services.intelligence.agents.agent_metadata import (
    AgentMetadata,
)

from services.intelligence.agents.agent_result import (
    AgentExecutionStatus,
    AgentResult,
)


from services.investigation_runtime.autonomous_investigation_intelligence_engine import (
    AutonomousInvestigationIntelligenceEngine,
)



class InvestigationAgent(BaseAgent):
    """
    Primary autonomous investigation agent.

    Responsibilities:

    - validate investigation context
    - create investigation workflow
    - execute autonomous investigation engine
    - return normalized AgentResult

    Non-responsibilities:

    - scheduling
    - runtime management
    - orchestration
    - retries
    """


    def __init__(self) -> None:

        self.engine = (
            AutonomousInvestigationIntelligenceEngine()
        )



    @property
    def metadata(
        self,
    ) -> AgentMetadata:

        return AgentMetadata(

            name="Investigation Agent",

            version="1.0",

            description=(
                "Executes autonomous AI investigations."
            ),

            investigation_types=[

                "phishing",

                "malware",

                "credential_access",

                "lateral_movement",

            ],

            tags=[

                "investigation",

                "planner",

                "autonomous",

            ],

        )



    @property
    def capabilities(
        self,
    ) -> list[AgentCapability]:

        return [

            AgentCapability(

                name="investigation_execution",

                description=(
                    "Executes autonomous security investigations"
                ),

                category="investigation",

            )

        ]



    def validate(
        self,
        context: AgentContext,
    ) -> bool:

        return bool(
            context.case_id
        )



    def execute(
        self,
        context: AgentContext,
    ) -> AgentResult:


        if not self.validate(context):

            return AgentResult(

                agent_name=self.metadata.name,

                status=(
                    AgentExecutionStatus.FAILED
                ),

                confidence=0.0,

                errors=[

                    "Invalid investigation context."

                ],

            )


        investigation_id = (
            context.case_id
        )


        self.engine.create_investigation(

            investigation_id=investigation_id,

            investigation_type="security_alert",

            severity="high",

        )


        analysis = self.engine.investigate(

            investigation_id

        )


        result = AgentResult(

            agent_name=self.metadata.name,

            status=(
                AgentExecutionStatus.SUCCESS
            ),

            confidence=90.0,

        )


        #
        # New autonomous investigation artifact
        #

        result.artifacts[

            "investigation_analysis"

        ] = analysis



        #
        # Backward compatibility artifact
        #
        # Existing consumers/tests expect
        # investigation_plan.
        #

        result.artifacts[

            "investigation_plan"

        ] = {

            "steps": analysis.get(

                "steps",

                [],

            )
            if isinstance(
                analysis,
                dict,
            )
            else [],


            "status": (

                analysis.get(

                    "status",

                    "completed",

                )

                if isinstance(
                    analysis,
                    dict,
                )

                else "completed"

            ),

        }



        result.metrics[

            "engine"

        ] = (

            "AutonomousInvestigationIntelligenceEngine"

        )



        return result



    def summarize(
        self,
        result: AgentResult,
    ) -> str:

        analysis = result.artifacts.get(

            "investigation_analysis",

            {},

        )


        steps = (

            analysis.get(

                "steps",

                [],

            )

            if isinstance(
                analysis,
                dict,
            )

            else []

        )


        return (

            "Autonomous investigation completed "

            f"with confidence "

            f"{result.confidence}%.\n"

            f"steps: {steps}"

        )



    def cleanup(
        self,
    ) -> None:

        """
        Cleanup hook required by BaseAgent.
        """

        pass