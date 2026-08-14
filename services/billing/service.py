from datetime import datetime, timezone
class BillingService:
    TIERS = {"trial": {"events": 10000, "users": 5, "retention_days": 7}, "professional": {"events": 1000000, "users": 25, "retention_days": 30}, "enterprise": {"events": 10000000, "users": 500, "retention_days": 365}}
    def __init__(self): self.usage = {}; self.tiers = {}
    def configure(self, organization_id, tier):
        if tier not in self.TIERS: raise ValueError("invalid_subscription_tier")
        self.tiers[organization_id] = tier; self.usage.setdefault(organization_id, {"events": 0, "users": 0, "api_calls": 0}); return self.status(organization_id)
    def consume(self, organization_id, metric, amount=1):
        tier = self.tiers.get(organization_id, "trial"); usage = self.usage.setdefault(organization_id, {"events": 0, "users": 0, "api_calls": 0}); limit = self.TIERS[tier].get(metric)
        if limit is not None and usage.get(metric, 0) + amount > limit: raise PermissionError("tenant_quota_exceeded")
        usage[metric] = usage.get(metric, 0) + amount; return usage[metric]
    def status(self, organization_id):
        tier = self.tiers.get(organization_id, "trial"); return {"organization_id": organization_id, "subscription_tier": tier, "limits": self.TIERS[tier], "usage": self.usage.setdefault(organization_id, {"events": 0, "users": 0, "api_calls": 0}), "updated_at": datetime.now(timezone.utc).isoformat()}
    def feature_allowed(self, organization_id, feature):
        return feature in {"telemetry", "detection", "investigation", "hunting", "copilot"} or self.tiers.get(organization_id, "trial") == "enterprise"
