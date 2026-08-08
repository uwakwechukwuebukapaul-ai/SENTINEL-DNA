from services.intelligence.investigator import (
    InvestigatorAgent,
)


class FakePipeline:

    def execute(
        self,
        case,
    ):

        return {
            "status": "completed"
        }



def test_investigation_execution():

    agent = InvestigatorAgent(
        pipeline=FakePipeline()
    )


    result = agent.investigate(
        {
            "id": "INC-001"
        }
    )


    assert (
        result["status"]
        == "completed"
    )



def test_pipeline_execution():

    agent = InvestigatorAgent(
        pipeline=FakePipeline()
    )


    result = agent.investigate({})


    assert (
        result["pipeline"]["status"]
        == "completed"
    )



def test_agent_history():

    agent = InvestigatorAgent()

    agent.investigate({})


    assert len(
        agent.get_history()
    ) == 1



def test_clear_history():

    agent = InvestigatorAgent()

    agent.investigate({})

    agent.clear_history()


    assert agent.get_history() == []