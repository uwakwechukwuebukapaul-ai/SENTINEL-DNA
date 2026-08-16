from services.core.application_container import build_container
from services.billing.application import BillingApplicationService
from services.billing.repository import BillingRepository
from services.billing.readiness import BillingRouteReadinessEvaluator

def test_container_constructs_provider_neutral_billing_dependencies_without_network():
    registry=build_container()
    assert isinstance(registry.require("billing_repository"),BillingRepository)
    assert isinstance(registry.require("billing_application"),BillingApplicationService)
    assert isinstance(registry.require("billing_readiness"),BillingRouteReadinessEvaluator)
    assert registry.require("billing_application").billing.provider is None
