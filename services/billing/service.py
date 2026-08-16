import secrets
from .models import PLANS, PaymentInitialization, SubscriptionStatus, Subscription, Entitlement
from .exceptions import BillingConfigurationError
class BillingService:
    TIERS={"trial":{"events":10000,"users":5,"retention_days":7},"professional":{"events":1000000,"users":25,"retention_days":30},"enterprise":{"events":10000000,"users":500,"retention_days":365}}
    def __init__(self, provider=None, plans=PLANS): self.provider=provider; self.plans=plans; self.usage={}; self.tiers={}; self.subscriptions={}; self.events=set()
    def configure(self, organization_id, tier):
        if tier not in self.TIERS: raise ValueError("invalid_subscription_tier")
        self.tiers[organization_id]=tier; self.usage.setdefault(organization_id,{"events":0,"users":0,"api_calls":0}); return self.status(organization_id)
    def consume(self, organization_id, metric, amount=1):
        tier=self.tiers.get(organization_id,"trial"); usage=self.usage.setdefault(organization_id,{"events":0,"users":0,"api_calls":0}); limit=self.TIERS[tier].get(metric)
        if limit is not None and usage.get(metric,0)+amount>limit: raise PermissionError("tenant_quota_exceeded")
        usage[metric]=usage.get(metric,0)+amount; return usage[metric]
    def status(self, organization_id):
        tier=self.tiers.get(organization_id,"trial"); from datetime import datetime,timezone
        return {"organization_id":organization_id,"subscription_tier":tier,"limits":self.TIERS[tier],"usage":self.usage.setdefault(organization_id,{"events":0,"users":0,"api_calls":0}),"updated_at":datetime.now(timezone.utc).isoformat()}
    def initialize_payment(self, tenant_id, plan_id, email, callback_url):
        if not self.provider or plan_id not in self.plans: raise BillingConfigurationError("billing_provider_unavailable")
        plan=self.plans[plan_id]; reference="sdna_"+secrets.token_urlsafe(24)
        result=self.provider.initialize_payment(email=email,reference=reference,amount_minor=plan.amount_minor,currency=plan.currency,callback_url=callback_url)
        return PaymentInitialization(tenant_id,reference,plan_id,plan.amount_minor,plan.currency,result.authorization_url)
    def process_event(self,event): self.events.add(event.get("id") or event.get("data",{}).get("reference"))
    def entitlement(self, tenant_id):
        sub=self.subscriptions.get(tenant_id); plan=self.plans.get(sub.plan_id if sub else "FREE"); return Entitlement(tenant_id,plan.plan_id,plan.capabilities if sub and sub.status in {SubscriptionStatus.ACTIVE,SubscriptionStatus.TRIAL} else frozenset())
    def feature_allowed(self, organization_id, feature): return feature in {"telemetry","detection","investigation","hunting","copilot"} or self.tiers.get(organization_id,"trial")=="enterprise"
