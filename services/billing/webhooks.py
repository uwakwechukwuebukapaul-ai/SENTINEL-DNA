import json
from .exceptions import WebhookVerificationError


class OperationalWebhookTenantResolver:
    """Resolve a webhook deployment to an active canonical tenant.

    Provider payload fields are intentionally absent from this contract. The
    mapping is supplied by trusted deployment configuration and resolved
    through the existing provider-tenant trust authority.
    """

    def __init__(self, trust_service, *, provider, issuer, external_tenant_id):
        if trust_service is None or not callable(getattr(trust_service, "resolve", None)):
            raise ValueError("provider_tenant_trust_service_required")
        values = (provider, issuer, external_tenant_id)
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("webhook_tenant_configuration_required")
        self._trust_service = trust_service
        self._provider, self._issuer, self._external_tenant_id = values

    def __call__(self):
        trust = self._trust_service.resolve(
            self._provider, self._issuer, self._external_tenant_id
        )
        tenant_id = getattr(trust, "canonical_tenant_id", "")
        if not tenant_id:
            raise WebhookVerificationError("canonical_webhook_tenant_unavailable")
        return tenant_id
class PaystackWebhookProcessor:
    def __init__(self, provider, service, transition_service=None, normalizer=None): self.provider, self.service, self.transition_service, self.normalizer, self.events = provider, service, transition_service, normalizer, set()
    def process(self, signature, body, tenant_id=None):
        if not self.provider.verify_webhook(signature, body): raise WebhookVerificationError("paystack_signature_invalid")
        try: event=json.loads(body); event_id=event.get("id") or event.get("data",{}).get("reference")
        except Exception as exc: raise WebhookVerificationError("paystack_payload_invalid") from exc
        if not isinstance(event,dict) or not event_id: raise WebhookVerificationError("paystack_payload_invalid")
        if self.transition_service:
            if callable(tenant_id):
                try: tenant_id = tenant_id()
                except Exception as exc: raise WebhookVerificationError("canonical_webhook_tenant_unavailable") from exc
            if not tenant_id: raise WebhookVerificationError("canonical_tenant_required")
            return self.transition_service.apply(self.normalizer.normalize(event, tenant_id))
        if event_id in self.events: return False
        self.events.add(event_id); self.service.process_event(event); return True
