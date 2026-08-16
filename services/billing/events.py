from dataclasses import dataclass
@dataclass(frozen=True)
class NormalizedBillingEvent:
    provider: str
    provider_event_id: str
    event_type: str
    tenant_id: str
    provider_transaction_reference: str|None = None
    provider_subscription_reference: str|None = None
    transaction_status: str|None = None
    subscription_status: str|None = None
    amount_minor: int|None = None
    currency: str|None = None
    occurred_at: str|None = None
    def validate(self):
        if not self.provider or not self.provider_event_id or not self.event_type or not self.tenant_id: raise ValueError("billing_event_incomplete")
        if not self.provider_transaction_reference and not self.provider_subscription_reference: raise ValueError("billing_reference_missing")
        if self.amount_minor is not None and self.amount_minor < 0: raise ValueError("billing_amount_invalid")
