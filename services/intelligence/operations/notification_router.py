"""Deterministic, provider-neutral notification routing decisions."""
from __future__ import annotations

from datetime import datetime, timezone


class OperationsNotificationRouter:
    def __init__(self, rule_repository=None, attempt_repository=None):
        self.rule_repository = rule_repository
        self.attempt_repository = attempt_repository

    def decide(self, *, tenant_id: str, alert: dict):
        rules = self.rule_repository.list_for_tenant(tenant_id=tenant_id) if self.rule_repository else []
        policy_id = str(alert.get("rule") or "")
        candidates = [rule for rule in rules if rule.get("policy_id") in {policy_id, "*"} and rule.get("enabled", True)]
        if not candidates:
            return {"status": "suppressed", "reason": "no_enabled_route", "policy_id": policy_id, "adapter": "deterministic-test", "destination": None}
        now = datetime.now(timezone.utc)
        for rule in candidates:
            severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
            threshold = rule.get("severity_threshold")
            if threshold and severity_order.get(str(alert.get("severity", "low")).lower(), 0) < severity_order.get(str(threshold).lower(), 0):
                continue
            suppression = rule.get("suppression_until")
            if suppression and datetime.fromisoformat(str(suppression).replace("Z", "+00:00")) > now:
                continue
            cooldown = int(rule.get("cooldown_seconds") or 0)
            if cooldown and self.attempt_repository:
                for attempt in reversed(self.attempt_repository.list_for_tenant(tenant_id=tenant_id)):
                    if attempt.get("alert_id") == alert.get("alert_id") and attempt.get("policy_id") == rule.get("policy_id"):
                        if (now - datetime.fromisoformat(str(attempt.get("attempted_at")).replace("Z", "+00:00"))).total_seconds() < cooldown:
                            break
                else:
                    return {"status": "pending", "reason": "route_selected", "policy_id": rule.get("policy_id"), "adapter": rule.get("adapter", "deterministic-test"), "destination": rule.get("destination")}
                continue
            return {"status": "pending", "reason": "route_selected", "policy_id": rule.get("policy_id"), "adapter": rule.get("adapter", "deterministic-test"), "destination": rule.get("destination")}
        return {"status": "suppressed", "reason": "suppression_window", "policy_id": policy_id, "adapter": "deterministic-test", "destination": None}
