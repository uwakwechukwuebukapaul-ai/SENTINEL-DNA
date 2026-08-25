from flask import Flask, g
from services.billing.governed_routes import create_governed_billing_blueprint
from services.billing.application import BillingApplicationService
from tests.credential_helpers import random_secret
def test_routes_fail_closed_without_trusted_context_provider():
    assert create_governed_billing_blueprint(object(),None) is None
def test_checkout_requires_csrf_and_status_uses_injected_context(monkeypatch):
    class App:
        def create_checkout_request(self,*args): raise AssertionError("csrf should stop request")
        def get_billing_status(self,*args): return type("Status",(),{"tenant_id":"a","subscription_status":None,"plan_id":None,"entitlement_capabilities":frozenset(),"transaction_reference":None,"transaction_status":None})()
    application=object.__new__(BillingApplicationService); application.get_billing_status=App().get_billing_status; application.create_checkout_request=App().create_checkout_request
    class Auth:
        def require(self,*args): return True
    bp=create_governed_billing_blueprint(application,lambda: type("Context",(),{"tenant_id":"a"})(),Auth())
    app=Flask(__name__); app.secret_key=random_secret(); app.register_blueprint(bp)
    client=app.test_client(); assert client.post("/api/billing/v2/checkout",json={"plan_id":"PRO"}).status_code==403; assert client.get("/api/billing/v2/status").status_code==200
