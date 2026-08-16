from dataclasses import dataclass
from .events import NormalizedBillingEvent
from .state_machine import require_transition, PAYMENT_TRANSITIONS, SUBSCRIPTION_TRANSITIONS
from .exceptions import BillingError
@dataclass(frozen=True)
class TransitionResult:
    event_id: str; applied: bool; duplicate: bool; old_status: str|None=None; new_status: str|None=None
class BillingStateTransitionService:
    def __init__(self, repository): self.repository=repository
    def apply(self, event: NormalizedBillingEvent):
        event.validate()
        with self.repository.transaction() as connection:
            if self.repository.event_exists(connection,event.provider_event_id): return TransitionResult(event.provider_event_id,False,True)
            self.repository.tenant_active(connection,event.tenant_id)
            old=new=None
            if event.provider_transaction_reference:
                row=self.repository.get_transaction(connection,event.provider_transaction_reference)
                if not row or row["tenant_id"] != event.tenant_id: raise BillingError("billing_transaction_tenant_mismatch")
                if event.amount_minor is not None and int(row["amount_minor"]) != event.amount_minor: raise BillingError("billing_amount_mismatch")
                if event.currency is not None and row["currency"] != event.currency: raise BillingError("billing_currency_mismatch")
                old=row["status"]; new=event.transaction_status or old
                if new != old: require_transition(PAYMENT_TRANSITIONS,old,new); self.repository.update_transaction(connection,event.provider_transaction_reference,new)
            if event.subscription_status:
                sub=self.repository.get_subscription(connection,event.tenant_id)
                if not sub: raise BillingError("billing_subscription_missing")
                old=sub["status"]; new=event.subscription_status
                if new != old: require_transition(SUBSCRIPTION_TRANSITIONS,old,new); self.repository.save_subscription(connection,event.tenant_id,sub["provider"],sub["plan_id"],new)
            if not self.repository.record_event(connection,event.provider_event_id,event.provider,event.event_type,event.provider_transaction_reference): return TransitionResult(event.provider_event_id,False,True)
            return TransitionResult(event.provider_event_id,True,False,old,new)
