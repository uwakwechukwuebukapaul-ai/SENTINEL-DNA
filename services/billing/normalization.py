from .events import NormalizedBillingEvent
from .exceptions import BillingError
class PaystackEventNormalizer:
    def normalize(self, payload, tenant_id):
        if not isinstance(payload,dict): raise BillingError("paystack_event_invalid")
        data=payload.get("data")
        if not isinstance(data,dict) or not payload.get("id") or not payload.get("event"): raise BillingError("paystack_event_invalid")
        if not isinstance(tenant_id,str) or not tenant_id: raise BillingError("canonical_tenant_required")
        status={"success":"SUCCESS","failed":"FAILED","abandoned":"CANCELLED"}.get(data.get("status"))
        event=NormalizedBillingEvent("paystack",str(payload["id"]),str(payload["event"]),tenant_id,str(data.get("reference")) if data.get("reference") else None,None,status,None,int(data["amount"]) if isinstance(data.get("amount"),int) else None,data.get("currency"),None)
        event.validate(); return event
