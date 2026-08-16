import json
from .exceptions import WebhookVerificationError
class PaystackWebhookProcessor:
    def __init__(self, provider, service): self.provider, self.service, self.events = provider, service, set()
    def process(self, signature, body):
        if not self.provider.verify_webhook(signature, body): raise WebhookVerificationError("paystack_signature_invalid")
        try: event=json.loads(body); event_id=event.get("id") or event.get("data",{}).get("reference")
        except Exception as exc: raise WebhookVerificationError("paystack_payload_invalid") from exc
        if not isinstance(event,dict) or not event_id: raise WebhookVerificationError("paystack_payload_invalid")
        if event_id in self.events: return False
        self.events.add(event_id); self.service.process_event(event); return True
