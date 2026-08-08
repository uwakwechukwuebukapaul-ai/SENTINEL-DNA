from services.intelligence.investigation.agent_result_collector import (
    AgentResultCollector,
)



def test_add_result():

    collector = AgentResultCollector()


    collector.add_result(
        "ioc_agent",
        {
            "ioc": 3
        },
    )


    assert (
        len(
            collector.get_results()
        )
        ==
        1
    )



def test_clear_results():

    collector = AgentResultCollector()


    collector.add_result(
        "risk_agent",
        {},
    )


    collector.clear()


    assert (
        collector.get_results()
        ==
        []
    )