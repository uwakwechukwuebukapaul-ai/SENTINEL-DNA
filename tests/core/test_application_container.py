"""
Sentinel DNA Application Container Tests.
"""

from services.core.application_container import (
    build_container,
)
from services.intelligence.investigation_optimizer import FeedbackRecommendationService



def test_container_build():

    container = build_container()


    assert container is not None



def test_case_manager_registered():

    container = build_container()


    service = container.get(
        "case_manager"
    )


    assert service is not None



def test_orchestrator_registered():

    container = build_container()


    service = container.get(
        "investigation_orchestrator"
    )


    assert service is not None



def test_dashboard_service_registered():

    container = build_container()


    service = container.get(
        "dashboard_service"
    )


    assert service is not None


def test_container_exposes_tenant_scoped_feedback_recommendation_factory():
    container = build_container()
    factory = container.get("feedback_recommendation_service_factory")

    service = factory("tenant-a")

    assert isinstance(service, FeedbackRecommendationService)
    assert service.optimizer.tenant_id == "tenant-a"
    assert service.optimizer.repository.list("tenant-a") == []
