"""Provider-neutral, canonical-tenant billing application boundary."""
from dataclasses import dataclass
from .exceptions import BillingError
from .models import PaymentInitialization

@dataclass(frozen=True)
class CheckoutRequest:
    plan_id: str
    email: str
    idempotency_key: str

@dataclass(frozen=True)
class BillingStatus:
    tenant_id: str
    subscription_status: str|None
    plan_id: str|None
    entitlement_capabilities: frozenset[str]
    transaction_reference: str|None
    transaction_status: str|None

class BillingApplicationService:
    def __init__(self, billing_service, repository, webhook_processor=None, entitlement_service=None):
        self.billing=billing_service; self.repository=repository; self.webhooks=webhook_processor; self.entitlements=entitlement_service or billing_service.entitlements
    @staticmethod
    def _tenant(context):
        tenant_id=getattr(context,"tenant_id",None)
        if not isinstance(tenant_id,str) or not tenant_id: raise BillingError("canonical_tenant_context_required")
        return tenant_id
    def create_checkout_request(self, context, request: CheckoutRequest):
        tenant_id=self._tenant(context)
        if not isinstance(request,CheckoutRequest) or not request.idempotency_key: raise BillingError("checkout_request_invalid")
        with self.repository.transaction() as connection:
            self.repository.tenant_active(connection,tenant_id)
            existing=self.repository.get_checkout(connection,tenant_id,request.idempotency_key)
            if existing: return PaymentInitialization(tenant_id,existing["transaction_reference"],existing["plan_id"],int(existing["amount_minor"]),existing["currency"],existing["authorization_url"])
        callback_url=getattr(self.billing.provider,"callback_url",None)
        if not callback_url: raise BillingError("billing_callback_not_configured")
        result=self.billing.initialize_payment(tenant_id,request.plan_id,request.email,callback_url)
        with self.repository.transaction() as connection:
            self.repository.save_checkout(connection,tenant_id,request.idempotency_key,result)
        return result
    def get_billing_status(self, context):
        tenant_id=self._tenant(context)
        with self.repository.transaction() as connection:
            self.repository.tenant_active(connection,tenant_id)
            subscription=self.repository.get_subscription(connection,tenant_id)
            transaction=self.repository.latest_transaction(connection,tenant_id)
        entitlement=self.entitlements.resolve(tenant_id,subscription)
        return BillingStatus(tenant_id,subscription["status"] if subscription else None,subscription["plan_id"] if subscription else None,entitlement.capabilities,transaction["transaction_reference"] if transaction else None,transaction["status"] if transaction else None)
    def process_verified_webhook(self, signature, body, canonical_tenant_id):
        if not self.webhooks: raise BillingError("webhook_boundary_unavailable")
        if not isinstance(canonical_tenant_id,str) or not canonical_tenant_id: raise BillingError("canonical_tenant_context_required")
        return self.webhooks.process(signature,body,canonical_tenant_id)
    def get_entitlements(self, context): return self.get_billing_status(context).entitlement_capabilities
