"""Deterministic operational alert evaluation over operations projections."""
from __future__ import annotations

import hashlib
from typing import Any


class OperationsAlertEvaluator:
    VERSION = "operational-alerts-v1"

    def evaluate(self, *, tenant_id: str, summary: dict[str, Any], trends: dict[str, Any], policies=None) -> list[dict[str, Any]]:
        tenant_id = str(tenant_id)
        now = str((trends.get("window") or {}).get("end") or "")
        alerts: list[dict[str, Any]] = []
        cases = summary.get("cases") or {}
        comparison = trends.get("comparison") or {}
        current = comparison.get("current") or {}
        previous = comparison.get("previous") or {}
        delta = comparison.get("delta") or {}
        policy_map = {item["rule"]: item for item in (policies or [])}
        defaults = {
            "sla_breach_risk": (0, "high"), "investigation_backlog": (10, "high"),
            "provider_failure_rate": (0.5, "high"), "confidence_degradation": (-0.1, "medium"),
            "escalation_volume": (5, "medium"), "analyst_workload_imbalance": (3, "medium"),
            "false_positive_spike": (3, "medium"),
        }
        def policy(rule):
            threshold, severity = defaults.get(rule, (0, "medium"))
            return policy_map.get(rule, {"threshold": threshold, "enabled": True, "severity": severity})
        if policy("sla_breach_risk").get("enabled", True) and cases.get("overdue_cases", 0) > float(policy("sla_breach_risk")["threshold"]):
            p = policy("sla_breach_risk"); alerts.append(self._alert(tenant_id, "sla_breach_risk", p["severity"], "One or more investigations are overdue.", "cases.overdue_cases", cases.get("overdue_cases", 0), ">", p["threshold"], now))
        if policy("investigation_backlog").get("enabled", True) and cases.get("active_cases", 0) >= float(policy("investigation_backlog")["threshold"]):
            p = policy("investigation_backlog"); alerts.append(self._alert(tenant_id, "investigation_backlog", p["severity"], "Active investigation backlog exceeded the operational threshold.", "cases.active_cases", cases.get("active_cases", 0), ">=", p["threshold"], now))
        for provider, rate in (summary.get("providers") or {}).get("failure_rate", {}).items():
            p = policy("provider_failure_rate")
            if p.get("enabled", True) and float(rate or 0) >= float(p["threshold"]):
                alerts.append(self._alert(tenant_id, "provider_failure_rate", p["severity"], f"Provider {provider} failure rate exceeded the operational threshold.", f"providers.failure_rate.{provider}", rate, ">=", p["threshold"], now, provider=provider))
        assignments = ((summary.get("analysts") or {}).get("by_actor") or {})
        loads = [float((value or {}).get("assigned_cases", 0)) for value in assignments.values()]
        if len(loads) >= 2 and max(loads) - min(loads) >= 3:
            alerts.append(self._alert(tenant_id, "analyst_workload_imbalance", "medium", "Analyst assigned-case distribution exceeded the imbalance threshold.", "analysts.by_actor.assigned_cases", max(loads) - min(loads), ">=", 3, now))
        p = policy("false_positive_spike")
        if p.get("enabled", True) and current.get("false_positives", 0) - previous.get("false_positives", 0) >= float(p["threshold"]):
            alerts.append(self._alert(tenant_id, "false_positive_spike", p["severity"], "False-positive volume increased materially versus the previous window.", "comparison.false_positives.delta", delta.get("false_positives", 0), ">=", p["threshold"], now))
        p = policy("confidence_degradation")
        if p.get("enabled", True) and delta.get("average_confidence", 0) <= float(p["threshold"]):
            alerts.append(self._alert(tenant_id, "confidence_degradation", p["severity"], "Average AI confidence declined versus the previous window.", "comparison.average_confidence.delta", delta.get("average_confidence", 0), "<=", p["threshold"], now))
        p = policy("escalation_volume")
        if p.get("enabled", True) and current.get("escalations", 0) >= float(p["threshold"]):
            alerts.append(self._alert(tenant_id, "escalation_volume", p["severity"], "Escalation volume exceeded the operational threshold.", "comparison.escalations", current.get("escalations", 0), ">=", p["threshold"], now))
        return sorted(alerts, key=lambda item: item["alert_id"])

    @staticmethod
    def _alert(tenant_id, rule, severity, reason, metric_source, observed_value, operator, threshold, detected_at, *, provider=None):
        identity = f"{tenant_id}|{rule}|{provider or ''}|{detected_at}"
        alert_id = "OAL-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        return {"version": OperationsAlertEvaluator.VERSION, "alert_id": alert_id, "tenant_id": tenant_id, "rule": rule, "severity": severity, "state": "detected", "reason": reason, "metric_source": metric_source, "observed_value": observed_value, "operator": operator, "threshold": threshold, "provider": provider, "detected_at": detected_at, "provenance": {"source": "operations_read_model", "read_only": True}}
