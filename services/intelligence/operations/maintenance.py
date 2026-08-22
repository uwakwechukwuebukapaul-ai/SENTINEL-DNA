"""Bounded, repeatable maintenance boundary for operations control-plane state."""
from __future__ import annotations

from datetime import datetime, timezone


class OperationsMaintenanceService:
    def __init__(self, operations_service):
        self.operations_service = operations_service

    def run(self, *, tenant_id: str, actor_id: str, now=None):
        now = now or datetime.now(timezone.utc)
        evaluations = self.operations_service.recover_expired_jobs(tenant_id=tenant_id, actor_id=actor_id, now=now)
        evaluations += self.operations_service.dispatch_due_jobs(tenant_id=tenant_id, actor_id=actor_id, now=now)
        notifications = self.operations_service.recover_notification_leases(tenant_id=tenant_id, actor_id=actor_id, now=now)
        notifications += self.operations_service.dispatch_notifications(tenant_id=tenant_id, actor_id=actor_id, now=now)
        summary = {"version": "operational-maintenance-v1", "tenant_id": str(tenant_id), "completed_at": now.isoformat(), "evaluations": evaluations, "notifications": notifications}
        audit = getattr(self.operations_service.read_model.coordinator, "audit_service", None)
        if audit:
            audit.record("OPERATIONS_MAINTENANCE_COMPLETED", user_id=actor_id, details={"tenant_id": str(tenant_id), "evaluation_count": len(evaluations), "notification_count": len(notifications)})
        return summary
