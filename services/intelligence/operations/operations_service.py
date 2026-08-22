"""Application service for the authenticated operations read boundary."""
from __future__ import annotations

from .operations_read_model import OperationsReadModel
from .operations_alerts import OperationsAlertEvaluator
from .operations_policy import OperationsAlertPolicyService
from .scheduler import DeterministicOperationsEvaluationScheduler
from .notifications import NotificationService
from .notification_router import OperationsNotificationRouter
from .governance_projection import OperationsGovernanceProjection
from .pagination import paginate, repository_page
from .maintenance import OperationsMaintenanceService


class OperationsService:
    def __init__(self, coordinator):
        self.read_model = OperationsReadModel(coordinator)
        self.alerts_evaluator = OperationsAlertEvaluator()
        self.policy_service = OperationsAlertPolicyService(getattr(coordinator, "operational_alert_policy_repository", None))
        self.assignment_repository = getattr(coordinator, "operational_alert_assignment_repository", None)
        self.assignment_directory = getattr(coordinator, "assignment_directory", None)
        self.evaluation_repository = getattr(coordinator, "operations_evaluation_repository", None)
        notification_repository = getattr(coordinator, "operational_notification_repository", None)
        self.notification_service = NotificationService(repository=notification_repository, audit=getattr(coordinator, "audit_service", None), router=OperationsNotificationRouter(getattr(coordinator, "operations_notification_rule_repository", None), notification_repository))

    def summary(self, *, tenant_id: str, actor_id: str | None = None) -> dict:
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        return self.read_model.build(tenant_id)

    def trends(self, *, tenant_id: str, actor_id: str | None = None, days: int = 30, now=None) -> dict:
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        return self.read_model.build_trends(tenant_id, days=days, now=now)

    def dashboard(self, *, tenant_id: str, actor_id: str | None = None, days: int = 30, now=None) -> dict:
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        summary = self.read_model.build(tenant_id, now=now)
        trends = self.read_model.build_trends(tenant_id, days=days, now=now)
        policies = self.policy_service.policies(tenant_id)
        alerts = self._materialize_alerts(tenant_id, summary, trends, actor_id=actor_id, policies=policies)
        return {"version": "operational-analytics-dashboard-v1", "control_plane_version": "operational-control-plane-v1", "tenant_id": str(tenant_id), "summary": summary, "trends": trends, "visualizations": self._visualizations(summary, trends), "alerts": alerts, "policy_status": {"version": self.policy_service.VERSION, "policies": policies}, "operational_health": self._health(alerts, policies), "governance": self._governance(tenant_id, alerts, policies)}

    def alerts(self, *, tenant_id: str, actor_id: str | None = None, days: int = 30, now=None, page=1, page_size=25) -> dict:
        dashboard = self.dashboard(tenant_id=tenant_id, actor_id=actor_id, days=days, now=now)
        paging = paginate(dashboard["alerts"], page=page, page_size=page_size)
        return {"version": "operational-alerts-v1", "tenant_id": str(tenant_id), "alerts": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}

    def policies(self, *, tenant_id: str, actor_id: str | None = None) -> dict:
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return {"version": self.policy_service.VERSION, "tenant_id": str(tenant_id), "policies": self.policy_service.policies(tenant_id)}

    def set_policy(self, rule: str, payload: dict, *, tenant_id: str, actor_id: str) -> dict:
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        value = self.policy_service.validate(rule, payload)
        repository = self.policy_service.repository
        if repository is None: raise RuntimeError("operational_policy_repository_unavailable")
        current = self.policy_service.policy(rule, tenant_id) or {}
        event = repository.append(tenant_id=tenant_id, rule=rule, actor_id=actor_id, reason=str(payload.get("reason") or "policy update"), previous_value={key: current.get(key) for key in ("threshold", "enabled", "severity")}, **value)
        audit = getattr(self.read_model.coordinator, "audit_service", None)
        if audit: audit.record("OPERATIONAL_ALERT_POLICY_UPDATED", user_id=actor_id, details={"tenant_id": str(tenant_id), "rule": rule, "threshold": value["threshold"], "enabled": value["enabled"], "severity": value["severity"]})
        return {"version": self.policy_service.VERSION, **event}

    def policy_history(self, *, tenant_id: str, actor_id: str | None = None, rule: str | None = None, page=1, page_size=25):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        repository = self.policy_service.repository
        paging = repository.page_history(tenant_id=tenant_id, rule=rule, page=page, page_size=page_size) if repository and callable(getattr(repository, "page_history", None)) else paginate(repository.history(tenant_id=tenant_id, rule=rule) if repository else [], page=page, page_size=page_size)
        return {"version": "operational-policy-history-v1", "tenant_id": str(tenant_id), "rule": rule, "history": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}

    def rollback_policy(self, rule: str, payload: dict, *, tenant_id: str, actor_id: str):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        history = self.policy_history(tenant_id=tenant_id, actor_id=actor_id, rule=rule)["history"]
        target = payload.get("version") or payload.get("event_id")
        item = next((entry for entry in history if str(entry.get("version")) == str(target) or entry.get("event_id") == str(target)), None)
        if item is None: raise LookupError("operational_policy_version_not_found")
        return self.set_policy(rule, {"threshold": item["threshold"], "enabled": item.get("enabled", True), "severity": item.get("severity", "medium"), "reason": payload.get("reason") or f"rollback to version {item.get('version')}"}, tenant_id=tenant_id, actor_id=actor_id)

    def assignments(self, alert_id: str, *, tenant_id: str, actor_id: str, page=1, page_size=25):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        paging = self.assignment_repository.page_history(alert_id, tenant_id=tenant_id, page=page, page_size=page_size) if self.assignment_repository and callable(getattr(self.assignment_repository, "page_history", None)) else paginate(self.assignment_repository.history(alert_id, tenant_id=tenant_id) if self.assignment_repository else [], page=page, page_size=page_size)
        return {"version": "operational-alert-assignments-v1", "tenant_id": str(tenant_id), "alert_id": str(alert_id), "assignments": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}

    def assign_alert(self, alert_id: str, payload: dict, *, tenant_id: str, actor_id: str):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        if self.assignment_repository is None: raise RuntimeError("operational_assignment_repository_unavailable")
        assignee = payload.get("assignee_id")
        if assignee and self.assignment_directory:
            self.assignment_directory.validate_target(tenant_id=tenant_id, actor_id=str(assignee))
        state = str(payload.get("state") or ("assigned" if assignee else "unassigned"))
        previous = self.assignment_repository.current(alert_id, tenant_id=tenant_id)
        event = self.assignment_repository.append(alert_id=alert_id, tenant_id=tenant_id, actor_id=actor_id, assignee_id=assignee, state=state, reason=payload.get("reason", ""))
        audit = getattr(self.read_model.coordinator, "audit_service", None)
        if audit: audit.record("OPERATIONAL_ALERT_ASSIGNMENT_CHANGED", user_id=actor_id, details={"tenant_id": str(tenant_id), "alert_id": str(alert_id), "previous_owner": previous.get("assignee_id"), "new_owner": event.get("assignee_id"), "state": state})
        return event

    def assignable_analysts(self, *, tenant_id: str, actor_id: str):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return {"version": "operational-assignable-analysts-v1", "tenant_id": str(tenant_id), "analysts": self.assignment_directory.list_for_tenant(tenant_id=tenant_id) if self.assignment_directory else []}

    def evaluations(self, *, tenant_id: str, actor_id: str, page=1, page_size=25):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        paging = repository_page(self.evaluation_repository, tenant_id=tenant_id, page=page, page_size=page_size) if self.evaluation_repository else paginate([], page=page, page_size=page_size)
        return {"version": "operational-evaluations-v1", "tenant_id": str(tenant_id), "evaluations": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}

    def evaluation(self, evaluation_id: str, *, tenant_id: str, actor_id: str):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return self.evaluation_repository.get(evaluation_id, tenant_id=tenant_id) if self.evaluation_repository else None

    def evaluate(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        if self.evaluation_repository is None: raise RuntimeError("operations_evaluation_repository_unavailable")
        return DeterministicOperationsEvaluationScheduler(self, self.evaluation_repository).evaluate(tenant_id=tenant_id, actor_id=actor_id, now=now)

    def notifications(self, *, tenant_id: str, actor_id: str, page=1, page_size=25):
        result = self.notification_service.list_for_tenant(tenant_id=tenant_id, actor_id=actor_id, page=page, page_size=page_size)
        repository = self.notification_service.repository
        paging = {"items": result["deliveries"], **(result.get("pagination") or {})} if result.get("pagination") else repository_page(repository, tenant_id=tenant_id, page=page, page_size=page_size) if repository else paginate([], page=page, page_size=page_size)
        return {**result, "deliveries": paging["items"], "pagination": {key: value for key, value in paging.items() if key != "items"}}

    def dispatch_notifications(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return self.notification_service.dispatch_pending(tenant_id=tenant_id, worker_id=f"notification-{actor_id}", now=now)

    def recover_notification_leases(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        repository = self.notification_service.repository; recovered = []
        if repository:
            for item in repository.list_expired_leases(tenant_id=tenant_id, now=now):
                recovered_item = repository.update(item["delivery_id"], tenant_id=tenant_id, status="retry_scheduled", detail="expired_notification_lease_recovered", retry_count=item.get("retry_count", 0))
                recovered.append(recovered_item)
        return [item for item in recovered if item]

    def notification_routes(self, *, tenant_id: str, actor_id: str):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        repository = getattr(self.read_model.coordinator, "operations_notification_rule_repository", None)
        return {"version": "operational-notification-routes-v1", "tenant_id": str(tenant_id), "routes": repository.list_for_tenant(tenant_id=tenant_id) if repository else []}

    def set_notification_route(self, payload: dict, *, tenant_id: str, actor_id: str, route_id: str | None = None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        repository = getattr(self.read_model.coordinator, "operations_notification_rule_repository", None)
        if repository is None: raise RuntimeError("notification_rule_repository_unavailable")
        adapter = str(payload.get("adapter", "deterministic-test")); allowed = {"deterministic-test", "email", "slack", "teams", "webhook"}
        if adapter not in allowed: raise ValueError("unsupported_notification_adapter")
        destination = payload.get("destination")
        if adapter in {"webhook", "slack", "teams"} and destination:
            from .notifications.providers import _safe_url
            _safe_url(destination)
        secret_reference = payload.get("secret_reference")
        if secret_reference and not str(secret_reference).startswith(("env://", "secret://")): raise ValueError("invalid_secret_reference")
        event = repository.append(tenant_id=tenant_id, policy_id=str(payload.get("policy_id") or "*"), adapter=adapter, destination=destination, secret_reference=secret_reference, enabled=bool(payload.get("enabled", True)), suppression_until=payload.get("suppression_until"), severity_threshold=payload.get("severity_threshold"), cooldown_seconds=payload.get("cooldown_seconds", 0), max_attempts=payload.get("max_attempts", 3), escalation_behavior=payload.get("escalation_behavior"), route_key=route_id)
        audit = getattr(self.read_model.coordinator, "audit_service", None)
        if audit: audit.record("OPERATIONAL_NOTIFICATION_ROUTE_UPDATED", user_id=actor_id, details={"tenant_id": str(tenant_id), "rule_id": event["rule_id"], "policy_id": event["policy_id"], "adapter": event["adapter"], "enabled": event["enabled"]})
        return event

    def governance_dashboard(self, *, tenant_id: str, actor_id: str, days: int = 30, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return OperationsGovernanceProjection(self).build(tenant_id=tenant_id, actor_id=actor_id, days=days, now=now)

    def enqueue_evaluation(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        if self.evaluation_repository is None: raise RuntimeError("operations_evaluation_repository_unavailable")
        from .scheduler import DeterministicOperationsEvaluationScheduler
        return DeterministicOperationsEvaluationScheduler(self, self.evaluation_repository).enqueue(tenant_id=tenant_id, actor_id=actor_id, now=now)

    def dispatch_due_jobs(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        from .scheduler import DeterministicOperationsEvaluationScheduler
        return DeterministicOperationsEvaluationScheduler(self, self.evaluation_repository).dispatch_due_jobs(tenant_id=tenant_id, actor_id=actor_id, now=now)

    def recover_expired_jobs(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        from .scheduler import DeterministicOperationsEvaluationScheduler
        return DeterministicOperationsEvaluationScheduler(self, self.evaluation_repository).recover_expired_jobs(tenant_id=tenant_id, actor_id=actor_id, now=now)

    def maintenance(self, *, tenant_id: str, actor_id: str, now=None):
        if not tenant_id or not actor_id: raise PermissionError("authenticated_tenant_context_required")
        return OperationsMaintenanceService(self).run(tenant_id=tenant_id, actor_id=actor_id, now=now)

    def alert(self, alert_id: str, *, tenant_id: str, actor_id: str | None = None, days: int = 30, now=None) -> dict | None:
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        repository = getattr(self.read_model.coordinator, "operational_alert_repository", None)
        if repository is not None:
            current = repository.latest(str(alert_id), tenant_id=str(tenant_id))
            if current:
                result = dict(current.get("alert") or {})
                result["state"] = current.get("state", "detected")
                result["tenant_id"] = str(tenant_id)
                result["lifecycle"] = {"last_event": current.get("event_kind"), "actor_id": current.get("actor_id")}
                return result
        result = self.alerts(tenant_id=tenant_id, actor_id=actor_id, days=days, now=now)
        return next((item for item in result["alerts"] if item["alert_id"] == str(alert_id)), None)

    def acknowledge_alert(self, alert_id: str, *, tenant_id: str, actor_id: str) -> dict | None:
        return self._transition_alert(alert_id, tenant_id=tenant_id, actor_id=actor_id, state="acknowledged")

    def resolve_alert(self, alert_id: str, *, tenant_id: str, actor_id: str) -> dict | None:
        return self._transition_alert(alert_id, tenant_id=tenant_id, actor_id=actor_id, state="resolved")

    def _materialize_alerts(self, tenant_id, summary, trends, *, actor_id, policies=None):
        alerts = self.alerts_evaluator.evaluate(tenant_id=tenant_id, summary=summary, trends=trends, policies=policies)
        repository = getattr(self.read_model.coordinator, "operational_alert_repository", None)
        if repository is None:
            return alerts
        result = []
        for alert in alerts:
            if not repository.has_detection(alert["alert_id"], tenant_id=tenant_id):
                repository.append(alert, tenant_id=tenant_id, event_kind="detected", state="detected", actor_id=actor_id)
            current = repository.latest(alert["alert_id"], tenant_id=tenant_id) or {"state": "detected"}
            alert["state"] = current.get("state", "detected")
            alert["lifecycle"] = {"last_event": current.get("event_kind", "detected"), "actor_id": current.get("actor_id")}
            result.append(alert)
        return result

    @staticmethod
    def _health(alerts, policies):
        active = [item for item in alerts if item.get("state") in {"detected", "acknowledged"}]
        critical = sum(item.get("severity") == "critical" for item in active)
        high = sum(item.get("severity") == "high" for item in active)
        factors = []
        if critical: factors.append("Critical operational alerts active")
        if high: factors.append("High-severity operational alerts active")
        overdue = sum(item.get("rule") == "sla_breach_risk" for item in active)
        if overdue: factors.append("SLA compliance below threshold")
        score = max(0, 100 - critical * 25 - high * 12 - max(0, len(active) - critical - high) * 5)
        status = "critical" if score < 50 or critical else "degraded" if score < 80 or high else "healthy"
        return {"status": status, "score": score, "factors": factors, "active_alerts": len(active), "critical_alerts": critical, "high_alerts": high, "enabled_policies": sum(item.get("enabled", True) for item in policies), "total_policies": len(policies)}

    def _governance(self, tenant_id, alerts, policies):
        ownership = {"unassigned_alerts": 0, "assigned_alerts": 0, "by_actor": {}}
        for alert in alerts:
            current = self.assignment_repository.current(alert["alert_id"], tenant_id=tenant_id) if self.assignment_repository else {"assignee_id": None}
            assignee = current.get("assignee_id")
            if assignee:
                ownership["assigned_alerts"] += 1; ownership["by_actor"][assignee] = ownership["by_actor"].get(assignee, 0) + 1
            else: ownership["unassigned_alerts"] += 1
        runs = self.evaluation_repository.list_for_tenant(tenant_id=tenant_id) if self.evaluation_repository else []
        return {"ownership": ownership, "policy_history_available": bool(self.policy_service.repository), "last_evaluation": runs[-1] if runs else None, "notifications": self.notification_service.list_for_tenant(tenant_id=tenant_id, actor_id="projection")["deliveries"]}

    def _transition_alert(self, alert_id, *, tenant_id, actor_id, state):
        if not tenant_id or not actor_id:
            raise PermissionError("authenticated_tenant_context_required")
        repository = getattr(self.read_model.coordinator, "operational_alert_repository", None)
        current = repository.latest(alert_id, tenant_id=tenant_id) if repository else None
        if not current:
            return None
        if state == "acknowledged" and current.get("state") != "detected":
            raise ValueError("invalid_operational_alert_transition")
        if state == "resolved" and current.get("state") not in {"detected", "acknowledged"}:
            raise ValueError("invalid_operational_alert_transition")
        repository.append(current["alert"], tenant_id=tenant_id, event_kind=state, state=state, actor_id=actor_id)
        audit = getattr(self.read_model.coordinator, "audit_service", None)
        if audit is not None:
            audit.record("OPERATIONAL_ALERT_" + state.upper(), user_id=actor_id, details={"tenant_id": str(tenant_id), "alert_id": str(alert_id), "state": state})
        result = dict(current["alert"]); result["state"] = state; result["lifecycle"] = {"last_event": state, "actor_id": actor_id}
        return result

    @staticmethod
    def _visualizations(summary, trends):
        series = trends.get("trends", [])
        return {"version": "operational-analytics-dashboard-v1", "charts": {
            "investigation_volume": {"series": [{"date": x["date"], "value": x["investigation_volume"]} for x in series]},
            "sla_compliance": {"series": [{"date": x["date"], "value": x["sla_compliance_rate"]} for x in series]},
            "escalations": {"series": [{"date": x["date"], "value": x["escalations"]} for x in series]},
            "false_positives": {"series": [{"date": x["date"], "value": x["false_positives"]} for x in series]},
            "ai_confidence": {"series": [{"date": x["date"], "value": x["average_confidence"]} for x in series]},
            "provider_reliability": {"series": [{"date": x["date"], "providers": x["provider_reliability"]} for x in series]},
            "analyst_workload": {"distribution": (summary.get("analysts") or {}).get("by_actor", {})}},
            "indicators": {"overdue_investigations": (summary.get("cases") or {}).get("overdue_cases", 0), "active_backlog": (summary.get("cases") or {}).get("active_cases", 0)}}
