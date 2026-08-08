from services.intelligence.orchestration import (
    InvestigationCoordinator,
    InvestigationPlan,
)


def test_investigation_coordinator():

    coordinator = InvestigationCoordinator()

    context = coordinator.create_context(
        "INC-001",
        [],
    )

    plan = InvestigationPlan(
        name="phishing investigation"
    )

    assert context.investigation_id == "INC-001"
    assert plan.name == "phishing investigation"