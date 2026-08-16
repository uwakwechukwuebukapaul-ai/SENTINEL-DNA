from flask import Flask
from services.billing.config import BillingConfiguration
from services.billing.readiness import BillingRouteReadinessEvaluator, register_if_ready

def complete():
    f=lambda: object()
    return dict(billing_application=object(),billing_service=object(),repository=object(),context_provider=f,authorization_provider=f,csrf_validator=f,webhook_verifier=f,webhook_tenant_resolver=f,payment_provider=object(),secret_reference="REF",billing_configuration=BillingConfiguration(True,"https://api.test","pk","REF","WEB","https://app.test/callback"))
def test_missing_dependencies_block_routes():
    result=BillingRouteReadinessEvaluator().evaluate(); assert result.state=="ROUTE_REGISTRATION_BLOCKED" and not result.ready and "canonical_request_context_unavailable" in result.reasons
def test_complete_injected_dependencies_are_ready_without_network():
    result=BillingRouteReadinessEvaluator().evaluate(**complete()); assert result.state=="READY_FOR_CONTROLLED_ROUTE_REGISTRATION" and result.ready
def test_registration_helper_is_fail_closed():
    app=Flask(__name__); bp=__import__("flask").Blueprint("b",__name__); blocked=BillingRouteReadinessEvaluator().evaluate(); assert not register_if_ready(app,bp,blocked); assert "b" not in [rule.endpoint for rule in app.url_map.iter_rules()]
def test_disabled_configuration_blocks_checkout():
    values=complete(); values["billing_configuration"]=BillingConfiguration(); result=BillingRouteReadinessEvaluator().evaluate(**values); assert not result.checkout_ready and not result.ready
