from services.intelligence.integration import (
    InvestigationIntegrator,
)

from services.intelligence.decision import (
    DecisionEngine,
)

from services.intelligence.recommendation import (
    RecommendationEngine,
)



def test_process_investigation():

    integrator = InvestigationIntegrator(
        decision_engine=DecisionEngine(),
        recommendation_engine=RecommendationEngine(),
    )


    result = integrator.process(
        {
            "id": "INV-100",
            "severity": "critical",
        }
    )


    assert (
        result["decision"]["decision"]
        == "respond"
    )



def test_recommendations_created():

    integrator = InvestigationIntegrator(
        recommendation_engine=RecommendationEngine(),
    )


    result = integrator.process(
        {
            "severity": "high",
        }
    )


    assert (
        "IOC blocking"
        in result["recommendations"]["recommendations"]
    )



def test_history():

    integrator = InvestigationIntegrator()


    integrator.process({})


    assert len(
        integrator.get_history()
    ) == 1



def test_clear_history():

    integrator = InvestigationIntegrator()


    integrator.process({})

    integrator.clear_history()


    assert integrator.get_history() == []