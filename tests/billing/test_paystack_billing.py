import hashlib, hmac, json
import pytest
from services.billing.models import PaymentStatus, SubscriptionStatus
from services.billing.paystack import PaystackPaymentProvider
from services.billing.service import BillingService
from services.billing.webhooks import PaystackWebhookProcessor
from services.billing.exceptions import BillingConfigurationError, WebhookVerificationError

class Secret:
    def get(self, reference): return "test-secret" if reference == "PAYSTACK" else ""
class Response:
    status_code=200
    def __init__(self,data): self.data=data
    def json(self): return {"status":True,"data":self.data}
class Transport:
    def post(self,*args,**kwargs): return Response({"authorization_url":"https://paystack.test/authorize"})
    def get(self,*args,**kwargs): return Response({"id":7,"status":"success","amount":1000,"currency":"NGN"})

def provider(): return PaystackPaymentProvider(base_url="https://api.paystack.test",secret_provider=Secret(),secret_reference="PAYSTACK",callback_url="https://app.test/billing/callback",transport=Transport())
def test_provider_requires_https_and_secret():
    with pytest.raises(BillingConfigurationError): PaystackPaymentProvider(base_url="http://api.test",secret_provider=Secret(),secret_reference="PAYSTACK",callback_url="https://app.test/callback")
    with pytest.raises(BillingConfigurationError): PaystackPaymentProvider(base_url="https://api.test",secret_provider=Secret(),secret_reference="MISSING",callback_url="https://app.test/callback")
def test_initialization_is_server_priced_and_references_canonical_tenant():
    service=BillingService(provider()); result=service.initialize_payment("tenant-a","PRO","user@example.com","https://app.test/billing/callback")
    assert result.tenant_id=="tenant-a" and result.amount_minor==0 and result.transaction_reference.startswith("sdna_")
def test_verification_is_server_side():
    assert provider().verify_payment("sdna_x").status == PaymentStatus.SUCCESS
def test_webhook_signature_and_idempotency():
    p=provider(); service=BillingService(p); processor=PaystackWebhookProcessor(p,service); body=json.dumps({"id":"evt-1","event":"charge.success"}).encode(); sig=hmac.new(b"test-secret",body,hashlib.sha512).hexdigest()
    assert processor.process(sig,body) is True and processor.process(sig,body) is False
    with pytest.raises(WebhookVerificationError): processor.process("bad",body)
def test_entitlements_are_separate_from_authorization():
    service=BillingService(); assert service.entitlement("tenant-a").capabilities==frozenset()
    service.subscriptions["tenant-a"]=type("Subscription",(),{"plan_id":"PRO","status":SubscriptionStatus.ACTIVE})()
    assert "investigations" in service.entitlement("tenant-a").capabilities
