"""Governed policy defaults and validation for operational alert evaluation."""
from __future__ import annotations

from typing import Any


class OperationsAlertPolicyService:
    VERSION = "operational-alert-policies-v1"
    DEFAULTS = {
        "sla_breach_risk": {"threshold": 0, "operator": ">", "severity": "high", "metric_source": "cases.overdue_cases"},
        "investigation_backlog": {"threshold": 10, "operator": ">=", "severity": "high", "metric_source": "cases.active_cases"},
        "provider_failure_rate": {"threshold": 0.5, "operator": ">=", "severity": "high", "metric_source": "providers.failure_rate"},
        "confidence_degradation": {"threshold": -0.1, "operator": "<=", "severity": "medium", "metric_source": "comparison.average_confidence.delta"},
        "escalation_volume": {"threshold": 5, "operator": ">=", "severity": "medium", "metric_source": "comparison.escalations"},
        "analyst_workload_imbalance": {"threshold": 3, "operator": ">=", "severity": "medium", "metric_source": "analysts.by_actor.assigned_cases"},
        "false_positive_spike": {"threshold": 3, "operator": ">=", "severity": "medium", "metric_source": "comparison.false_positives.delta"},
    }

    def __init__(self, repository=None):
        self.repository = repository

    def policies(self, tenant_id: str) -> list[dict[str, Any]]:
        configured = {item["rule"]: item for item in (self.repository.list_for_tenant(tenant_id=tenant_id) if self.repository else [])}
        result = []
        for rule, default in self.DEFAULTS.items():
            current = dict(default); current.update(configured.get(rule) or {})
            current.setdefault("policy_version", configured.get(rule, {}).get("version", 0) if rule in configured else 0)
            current.setdefault("changed_by", None)
            current.setdefault("changed_at", None)
            current.setdefault("reason", "default policy" if rule not in configured else "policy update")
            current.update({"version": self.VERSION, "tenant_id": str(tenant_id), "rule": rule})
            result.append(current)
        return result

    def policy(self, rule: str, tenant_id: str):
        return next((item for item in self.policies(tenant_id) if item["rule"] == str(rule)), None)

    def validate(self, rule: str, payload: dict[str, Any]) -> dict[str, Any]:
        if str(rule) not in self.DEFAULTS:
            raise ValueError("unknown_operational_alert_policy")
        try:
            threshold = float(payload["threshold"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("policy_threshold_required")
        severity = str(payload.get("severity", self.DEFAULTS[str(rule)]["severity"])).lower()
        if severity not in {"low", "medium", "high", "critical"}:
            raise ValueError("invalid_policy_severity")
        if rule in {"provider_failure_rate"} and not 0 <= threshold <= 1:
            raise ValueError("provider_failure_rate_threshold_out_of_range")
        if rule == "confidence_degradation" and threshold > 0:
            raise ValueError("confidence_degradation_threshold_invalid")
        return {"threshold": threshold, "enabled": bool(payload.get("enabled", True)), "severity": severity}
