"""
Sentinel DNA Investigation Plan

Defines the execution blueprint
for autonomous investigations.
"""


class InvestigationPlan:
    """
    Investigation workflow plan.

    Backward compatible with:
    - investigation_id
    - case_id
    - name
    - plan_name
    - agents
    - stages
    """

    def __init__(
        self,
        investigation_id=None,
        case_id=None,
        name=None,
        plan_name=None,
        agents=None,
        stages=None,
    ):

        self.investigation_id = (
            investigation_id
            or case_id
            or "UNKNOWN"
        )

        self.case_id = (
            case_id
            or self.investigation_id
        )

        self.name = (
            name
            or plan_name
            or "Investigation Plan"
        )

        self.plan_name = self.name

        self.agents = (
            agents
            or []
        )

        self.stages = (
            stages
            or []
        )


    def add_stage(
        self,
        stage,
    ):
        """
        Add workflow stage.
        """

        self.stages.append(
            stage
        )


    def add_agent(
        self,
        agent,
    ):
        """
        Register execution agent.
        """

        self.agents.append(
            agent
        )


    def to_dict(self):
        return {

            "investigation_id":
                self.investigation_id,

            "case_id":
                self.case_id,

            "name":
                self.name,

            "agents":
                self.agents,

            "stages":
                self.stages,

        }