from .models import PLANS, Entitlement, SubscriptionStatus
class EntitlementService:
    def __init__(self, plans=PLANS): self.plans=plans
    def resolve(self, tenant_id, subscription):
        plan=self.plans.get(subscription["plan_id"] if subscription else "FREE")
        active=subscription and subscription["status"] in {SubscriptionStatus.ACTIVE.value,SubscriptionStatus.TRIAL.value}
        return Entitlement(tenant_id,plan.plan_id,plan.capabilities if active else frozenset())
