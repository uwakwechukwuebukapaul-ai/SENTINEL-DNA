"""Authenticated application boundary for future notification providers."""
from __future__ import annotations


class NotificationService:
    def __init__(self, adapter=None, repository=None, audit=None, router=None, provider_adapters=None):
        from .adapters import DeterministicTestNotificationAdapter
        self.adapter = adapter or DeterministicTestNotificationAdapter()
        self.repository = repository
        self.audit = audit
        self.router = router
        from .providers import configured_provider_adapters
        self.provider_adapters = {**configured_provider_adapters(), **(provider_adapters or {})}

    def deliver(self, *, tenant_id: str, actor_id: str, alert: dict, recipient: str | None = None):
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        route = self.router.decide(tenant_id=tenant_id, alert=alert) if self.router else {"status": "pending", "policy_id": alert.get("rule", ""), "adapter": self.adapter.name, "destination": recipient}
        from .adapters import DeterministicEmailNotificationAdapter, DeterministicSlackNotificationAdapter, DeterministicTeamsNotificationAdapter, DeterministicWebhookNotificationAdapter
        adapter = {"email": DeterministicEmailNotificationAdapter(), "slack": DeterministicSlackNotificationAdapter(), "teams": DeterministicTeamsNotificationAdapter(), "webhook": DeterministicWebhookNotificationAdapter(), "deterministic-test": self.adapter, **self.provider_adapters}.get(route.get("adapter"), self.adapter)
        if route["status"] == "suppressed":
            result = {"status": "suppressed", "adapter": route["adapter"], "tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "reason": route["reason"]}
        else:
            result = adapter.deliver(tenant_id=str(tenant_id), alert=alert, recipient=route.get("destination") or recipient)
            result["routing"] = route
        if self.repository:
            key = f"{tenant_id}|{alert['alert_id']}|{route.get('policy_id', alert.get('rule', ''))}|{result['adapter']}|{route.get('destination') or recipient or ''}"
            attempt = self.repository.append(tenant_id=tenant_id, alert_id=alert["alert_id"], policy_id=route.get("policy_id", alert.get("rule", "")), adapter=result["adapter"], status="sent" if result["status"] == "simulated" else result["status"], actor_source=actor_id, destination=route.get("destination") or recipient, suppression_reason=route.get("reason") if route.get("status") == "suppressed" else None, idempotency_key=key)
            result = {**result, "delivery": attempt}
        if self.audit:
            self.audit.record("OPERATIONAL_NOTIFICATION_DELIVERY_ATTEMPT", user_id=actor_id, details={"tenant_id": str(tenant_id), "alert_id": str(alert["alert_id"]), "adapter": result.get("adapter"), "status": result.get("status")})
        return result

    def enqueue(self, *, tenant_id: str, actor_id: str, alert: dict, recipient: str | None = None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        route = self.router.decide(tenant_id=tenant_id, alert=alert) if self.router else {"status": "pending", "policy_id": alert.get("rule", ""), "adapter": self.adapter.name, "destination": recipient}
        key = f"{tenant_id}|{alert['alert_id']}|{route.get('policy_id', alert.get('rule', ''))}|{route.get('adapter')}|{route.get('destination') or recipient or ''}"
        status = "suppressed" if route["status"] == "suppressed" else "pending"
        return self.repository.append(tenant_id=tenant_id, alert_id=alert["alert_id"], policy_id=route.get("policy_id", alert.get("rule", "")), adapter=route.get("adapter", self.adapter.name), actor_source=actor_id, destination=route.get("destination") or recipient, status=status, suppression_reason=route.get("reason"), idempotency_key=key) if self.repository else {"status": status, "idempotency_key": key}

    def list_for_tenant(self, *, tenant_id: str, actor_id: str, page=None, page_size=25):
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        if self.repository and page is not None and callable(getattr(self.repository, "page_for_tenant", None)):
            paging = self.repository.page_for_tenant(tenant_id=tenant_id, page=page, page_size=page_size)
            return {"version": "operational-notifications-v1", "tenant_id": str(tenant_id), "deliveries": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}
        return {"version": "operational-notifications-v1", "tenant_id": str(tenant_id), "deliveries": self.repository.list_for_tenant(tenant_id=tenant_id) if self.repository else []}

    def dispatch_pending(self, *, tenant_id: str, worker_id: str, now=None, lease_seconds: int = 300, max_attempts: int = 3):
        from ..retry_policy import OperationsRetryPolicy
        from .adapters import DeterministicEmailNotificationAdapter, DeterministicSlackNotificationAdapter, DeterministicTeamsNotificationAdapter, DeterministicWebhookNotificationAdapter
        adapters = {"email": DeterministicEmailNotificationAdapter(), "slack": DeterministicSlackNotificationAdapter(), "teams": DeterministicTeamsNotificationAdapter(), "webhook": DeterministicWebhookNotificationAdapter(), "deterministic-test": self.adapter, **self.provider_adapters}
        results = []
        items = self.repository.list_dispatchable(tenant_id=tenant_id, now=now, limit=100) if self.repository and callable(getattr(self.repository, "list_dispatchable", None)) else self.repository.list_for_tenant(tenant_id=tenant_id) if self.repository else []
        for item in items:
            if item.get("status") not in {"pending", "retry_scheduled"} or (item.get("next_attempt_at") and now and item["next_attempt_at"] > now.isoformat()): continue
            lease = self.repository.acquire_lease(item["delivery_id"], tenant_id=tenant_id, worker_id=worker_id, lease_seconds=lease_seconds, now=now)
            if not lease: continue
            adapter = adapters.get(lease.get("adapter"), self.adapter)
            try:
                self.repository.update(lease["delivery_id"], tenant_id=tenant_id, status="sending", detail="delivery_started", lease_id=lease["lease_id"], worker_id=worker_id)
                value = adapter.deliver(tenant_id=tenant_id, alert={"alert_id": lease["alert_id"]}, recipient=lease.get("destination"))
                result = self.repository.update(lease["delivery_id"], tenant_id=tenant_id, status="delivered", detail="delivery_complete", lease_id=lease["lease_id"], worker_id=worker_id)
            except Exception as error:
                decision = OperationsRetryPolicy(max_retries=max_attempts).decide(retry_count=int(lease.get("retry_count", 0)), category=OperationsRetryPolicy().classify(error), now=now)
                history = list(lease.get("attempt_history", [])); history.append({"attempt": decision.retry_count, "category": decision.category, "outcome": "retry_scheduled" if decision.retry else "dead_lettered"})
                result = self.repository.update(lease["delivery_id"], tenant_id=tenant_id, status="retry_scheduled" if decision.retry else "dead_lettered", detail=decision.reason, retry_count=decision.retry_count, next_attempt_at=decision.next_attempt_at, attempt_history=history, lease_id=lease["lease_id"], worker_id=worker_id)
            self.repository.release_lease(lease["delivery_id"], tenant_id=tenant_id, worker_id=worker_id, lease_id=lease["lease_id"], now=now)
            if self.audit:
                event = "OPERATIONAL_NOTIFICATION_DELIVERED" if result and result.get("status") == "delivered" else "OPERATIONAL_NOTIFICATION_DEAD_LETTERED" if result and result.get("status") == "dead_lettered" else "OPERATIONAL_NOTIFICATION_RETRIED"
                self.audit.record(event, user_id=worker_id, details={"tenant_id": str(tenant_id), "delivery_id": lease["delivery_id"], "alert_id": lease["alert_id"], "adapter": lease.get("adapter"), "status": result.get("status") if result else "lease_lost"})
            if result: results.append(result)
        return results
