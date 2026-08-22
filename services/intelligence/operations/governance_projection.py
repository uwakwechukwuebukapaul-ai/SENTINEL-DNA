"""Additive manager-facing governance projection over existing operations data."""
from __future__ import annotations


class OperationsGovernanceProjection:
    VERSION = "operational-governance-dashboard-v1"

    def __init__(self, operations_service):
        self.operations_service = operations_service

    def build(self, *, tenant_id: str, actor_id: str, days: int = 30, now=None):
        dashboard = self.operations_service.dashboard(tenant_id=tenant_id, actor_id=actor_id, days=days, now=now)
        alerts = dashboard.get("alerts", [])
        assignment = {"alerts": [], "unassigned": 0, "by_actor": {}}
        for alert in alerts:
            current = self.operations_service.assignment_repository.current(alert["alert_id"], tenant_id=tenant_id) if self.operations_service.assignment_repository else {"state": "unassigned", "assignee_id": None}
            assignment["alerts"].append({"alert_id": alert["alert_id"], "assignee_id": current.get("assignee_id"), "state": current.get("state", "unassigned"), "last_event": current.get("created_at")})
            if current.get("assignee_id"):
                assignment["by_actor"][current["assignee_id"]] = assignment["by_actor"].get(current["assignee_id"], 0) + 1
            else:
                assignment["unassigned"] += 1
        runs = self.operations_service.evaluation_repository.list_for_tenant(tenant_id=tenant_id) if self.operations_service.evaluation_repository else []
        notifications = self.operations_service.notifications(tenant_id=tenant_id, actor_id=actor_id)
        policies = dashboard.get("policy_status", {}).get("policies", [])
        history = {item["rule"]: self.operations_service.policy_history(tenant_id=tenant_id, actor_id=actor_id, rule=item["rule"])["history"] for item in policies}
        route_repository = getattr(self.operations_service.read_model.coordinator, "operations_notification_rule_repository", None)
        routes = route_repository.list_for_tenant(tenant_id=tenant_id) if route_repository else []
        run_counts = {status: sum(item.get("status") == status for item in runs) for status in ("queued", "leased", "running", "completed", "retry_scheduled", "failed", "dead_lettered", "cancelled")}
        delivery_counts = {status: sum(item.get("status") == status for item in notifications.get("deliveries", [])) for status in ("pending", "sent", "delivered", "retry_scheduled", "failed", "dead_lettered", "suppressed")}
        audit_timeline = []
        for item in sum(history.values(), []): audit_timeline.append({"type": "policy_change", "at": item.get("created_at"), "actor_id": item.get("changed_by") or item.get("actor_id"), "rule": item.get("rule"), "version": item.get("version")})
        for item in runs: audit_timeline.append({"type": "evaluation", "at": item.get("started_at"), "actor_id": item.get("initiator"), "evaluation_id": item.get("evaluation_id"), "status": item.get("status")})
        for item in notifications.get("deliveries", []): audit_timeline.append({"type": "notification", "at": item.get("attempted_at"), "actor_id": item.get("actor_source"), "alert_id": item.get("alert_id"), "status": item.get("status")})
        return {"version": self.VERSION, "tenant_id": str(tenant_id), "analytics": dashboard, "policy_governance": {"current": policies, "history": history}, "assignment_governance": assignment, "evaluation_governance": {"last_run": runs[-1] if runs else None, "runs": runs, "counts": run_counts}, "notification_governance": {**notifications, "counts": delivery_counts}, "routing_governance": {"routes": routes, "enabled": sum(bool(item.get("enabled")) for item in routes), "disabled": sum(not bool(item.get("enabled")) for item in routes)}, "audit_timeline": sorted(audit_timeline, key=lambda item: item.get("at") or "", reverse=True)}
