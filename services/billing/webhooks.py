import json
from .exceptions import WebhookVerificationError
class PaystackWebhookProcessor:
    def __init__(self, provider, service, transition_service=None, normalizer=None): self.provider, self.service, self.transition_service, self.normalizer, self.events = provider, service, transition_service, normalizer, set()
    def process(self, signature, body, tenant_id=None):
        if not self.provider.verify_webhook(signature, body): raise WebhookVerificationError("paystack_signature_invalid")
        try: event=json.loads(body); event_id=event.get("id") or event.get("data",{}).get("reference")
        except Exception as exc: raise WebhookVerificationError("paystack_payload_invalid") from exc
        if not isinstance(event,dict) or not event_id: raise WebhookVerificationError("paystack_payload_invalid")
        if self.transition_service:
            if not tenant_id: raise WebhookVerificationError("canonical_tenant_required")
            return self.transition_service.apply(self.normalizer.normalize(event, tenant_id))
        if event_id in self.events: return False
        self.events.add(event_id); self.service.process_event(event); return True
