"""Derived, tenant-scoped operations read model.

This module deliberately does not persist a second case or execution store. It
projects the existing append-only repositories into manager-facing metrics.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from .operations_metrics import AnalystMetrics, InvestigationMetrics, ProviderMetrics


def _time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _first(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return default


class OperationsReadModel:
    VERSION = "operations-summary-v1"
    TRENDS_VERSION = "operational-analytics-v1"

    def __init__(self, coordinator: Any):
        self.coordinator = coordinator

    def _tenant_rows(self, repository: Any, method: str, tenant_id: str) -> list[dict[str, Any]]:
        reader = getattr(repository, method, None)
        if not callable(reader):
            return []
        try:
            return list(reader(tenant_id=str(tenant_id)))
        except TypeError:
            # Legacy canonical repositories use a positional tenant argument.
            return list(reader(str(tenant_id)))

    def build(self, tenant_id: str, *, now: datetime | None = None) -> dict[str, Any]:
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise PermissionError("tenant_context_required")
        now = now or datetime.now(timezone.utc)
        executions = self._tenant_rows(self.coordinator.execution_repository, "list_for_tenant", tenant_id)
        reviews = self._tenant_rows(self.coordinator.evidence_review_repository, "list_for_tenant", tenant_id)
        lifecycle = self._tenant_rows(self.coordinator.case_lifecycle_repository, "list_for_tenant", tenant_id)
        intelligence = self._tenant_rows(self.coordinator.intelligence_repository, "list_for_tenant", tenant_id)
        reports = self._tenant_rows(self.coordinator.report_repository, "list_for_tenant", tenant_id)

        by_case: dict[str, dict[str, Any]] = {}
        for row in executions:
            case_id = str(row.get("case_id") or row.get("investigation_id") or "")
            if case_id:
                by_case.setdefault(case_id, {})["execution"] = row
        for row in intelligence + reports:
            case_id = str(row.get("case_id") or "")
            if case_id:
                by_case.setdefault(case_id, {})["intelligence" if row in intelligence else "report"] = row
        for row in lifecycle:
            case_id = str(row.get("case_id") or "")
            if case_id:
                by_case.setdefault(case_id, {}).setdefault("lifecycle", []).append(row)

        latest_reviews: dict[str, dict[str, Any]] = {}
        for row in reviews:
            latest_reviews[str(row.get("evidence_id"))] = row
        pending_states = {"pending_review", "assigned", "in_review", "reviewed", "requires_escalation"}
        terminal_states = {"accepted", "rejected", "completed"}
        pending_reviews = sum(1 for row in latest_reviews.values() if row.get("new_state") in pending_states)
        completed_reviews = sum(1 for row in latest_reviews.values() if row.get("new_state") in terminal_states)

        resolution_times: list[float] = []
        confidences: list[float] = []
        high_risk = 0
        active = closed = reopened = overdue = 0
        risk_distribution: dict[str, int] = {}
        confidence_trend: list[dict[str, Any]] = []
        for case_id, data in by_case.items():
            events = data.get("lifecycle", [])
            latest_case = events[-1] if events else {}
            state = str(latest_case.get("state") or "open")
            if state == "closed": closed += 1
            else: active += 1
            if any(event.get("state") == "reopened" or event.get("event_kind") == "case_reopened" for event in events): reopened += 1
            sla = next((event for event in reversed(events) if event.get("event_kind") == "sla"), None)
            deadline = _first(sla.get("details", {}) if sla else {}, "response_deadline", "review_deadline")
            if (sla and sla.get("state") == "overdue") or (_time(deadline) and _time(deadline) < now and state != "closed"): overdue += 1
            opened = next((_time(event.get("created_at")) for event in events if event.get("event_kind") in {"case_lifecycle", "investigation_started"}), None)
            closed_at = next((_time(event.get("created_at")) for event in reversed(events) if event.get("state") == "closed"), None)
            execution = data.get("execution") or {}
            opened = opened or _time(execution.get("started_at"))
            if execution.get("status") in {"SUCCESS", "completed", "closed"}:
                closed_at = closed_at or _time(execution.get("completed_at"))
            if opened and closed_at:
                resolution_times.append(max(0.0, (closed_at - opened).total_seconds()))
            source = data.get("report") or data.get("intelligence") or execution
            confidence = _number(_first(source, "confidence", "confidence_score", default=0))
            risk = _number(_first(source, "risk_score", "risk", default=0))
            if isinstance(source.get("risk"), dict): risk = _number(source["risk"].get("score"), risk)
            if confidence: confidences.append(confidence)
            if risk >= 70: high_risk += 1
            band = "high" if risk >= 70 else "medium" if risk >= 40 else "low"
            risk_distribution[band] = risk_distribution.get(band, 0) + 1
            confidence_trend.append({"case_id": case_id, "confidence": confidence, "observed_at": source.get("updated_at") or source.get("created_at")})

        analyst = self._analyst_metrics(lifecycle, reviews)
        provider = self._provider_metrics(executions)
        investigations = InvestigationMetrics(
            total_cases=len(by_case), active_cases=active, closed_cases=closed, reopened_cases=reopened,
            overdue_cases=overdue, average_resolution_time=round(sum(resolution_times) / len(resolution_times), 2) if resolution_times else 0.0,
            average_confidence=round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
            high_risk_cases=high_risk, evidence_review_pending=pending_reviews, evidence_review_completed=completed_reviews,
        )
        return {"version": self.VERSION, "tenant_id": tenant_id, "cases": investigations.to_dict(), "analysts": analyst.to_dict(), "providers": provider.to_dict(), "risk": {"distribution": risk_distribution}, "compliance": {"overdue_cases": overdue, "review_pending": pending_reviews}, "trends": {"confidence": confidence_trend}}

    def build_trends(self, tenant_id: str, *, days: int = 30, now: datetime | None = None) -> dict[str, Any]:
        """Build deterministic daily analytics for the requested tenant.

        The previous window is calculated from the same repositories and the
        same bucket rules, which makes comparisons reproducible in tests and
        suitable for future scheduled dashboard refreshes.
        """
        tenant_id = str(tenant_id or "").strip()
        if not tenant_id:
            raise PermissionError("tenant_context_required")
        days = max(1, min(int(days), 365))
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        now = now.astimezone(timezone.utc)
        executions = self._tenant_rows(self.coordinator.execution_repository, "list_for_tenant", tenant_id)
        lifecycle = self._tenant_rows(self.coordinator.case_lifecycle_repository, "list_for_tenant", tenant_id)
        intelligence = self._tenant_rows(self.coordinator.intelligence_repository, "list_for_tenant", tenant_id)
        reports = self._tenant_rows(self.coordinator.report_repository, "list_for_tenant", tenant_id)
        reviews = self._tenant_rows(self.coordinator.evidence_review_repository, "list_for_tenant", tenant_id)

        current_end = now
        current_start = current_end - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)
        current = self._trend_window(current_start, current_end, executions, lifecycle, intelligence, reports, reviews, days)
        previous = self._trend_window(previous_start, current_start, executions, lifecycle, intelligence, reports, reviews, days)
        current_totals = self._trend_totals(current)
        previous_totals = self._trend_totals(previous)
        comparison = {key: round(current_totals[key] - previous_totals[key], 4) for key in current_totals}
        return {
            "version": self.TRENDS_VERSION,
            "tenant_id": tenant_id,
            "window": {"days": days, "start": current_start.isoformat(), "end": current_end.isoformat()},
            "trends": current,
            "comparison": {"current": current_totals, "previous": previous_totals, "delta": comparison},
        }

    @staticmethod
    def _trend_window(start, end, executions, lifecycle, intelligence, reports, reviews, days):
        labels = [(start + timedelta(days=index)).date().isoformat() for index in range(days)]
        buckets = {label: {"investigation_volume": 0, "average_resolution_time": 0.0, "resolution_samples": 0, "sla_compliant": 0, "sla_observed": 0, "assignments": 0, "escalations": 0, "false_positives": 0, "dispositions": 0, "confidence_sum": 0.0, "confidence_samples": 0, "providers": {}} for label in labels}

        def bucket(value):
            parsed = _time(value)
            if parsed is None or parsed < start or parsed >= end:
                return None
            return parsed.astimezone(timezone.utc).date().isoformat()

        cases_by_day: dict[str, set[str]] = {label: set() for label in labels}
        for execution in executions:
            label = bucket(execution.get("started_at") or execution.get("created_at"))
            case_id = str(execution.get("case_id") or execution.get("investigation_id") or "")
            if label and case_id:
                cases_by_day[label].add(case_id)
            completed = _time(execution.get("completed_at"))
            started = _time(execution.get("started_at"))
            completion_label = bucket(execution.get("completed_at"))
            if completion_label and started and completed and completed >= started:
                buckets[completion_label]["average_resolution_time"] += (completed - started).total_seconds()
                buckets[completion_label]["resolution_samples"] += 1
            for provider, raw in (execution.get("provider_states") or execution.get("providers") or {}).items() if isinstance(execution.get("provider_states") or execution.get("providers") or {}, dict) else []:
                observation = raw if isinstance(raw, dict) else {"status": raw}
                provider_label = bucket(execution.get("completed_at") or execution.get("started_at"))
                if provider_label:
                    record = buckets[provider_label]["providers"].setdefault(str(provider), {"observations": 0, "failures": 0, "unavailable": 0, "latency_sum": 0.0, "latency_samples": 0})
                    status = str(_first(observation, "status", "health_status", "availability_state", default="UNAVAILABLE")).upper()
                    record["observations"] += 1
                    record["failures"] += int(status in {"FAILED", "BLOCKED"})
                    record["unavailable"] += int(status in {"UNAVAILABLE", "FAILED", "BLOCKED"})
                    latency = _first(observation, "latency_ms", "latency")
                    if latency is not None:
                        record["latency_sum"] += _number(latency)
                        record["latency_samples"] += 1
        for label, cases in cases_by_day.items():
            buckets[label]["investigation_volume"] = len(cases)
        for event in lifecycle:
            label = bucket(event.get("created_at"))
            if not label:
                continue
            kind = str(event.get("event_kind") or "")
            details = event.get("details") or {}
            if kind == "sla":
                buckets[label]["sla_observed"] += 1
                buckets[label]["sla_compliant"] += int(event.get("state") not in {"overdue", "failed"})
            if kind == "assignment": buckets[label]["assignments"] += 1
            if kind == "escalation": buckets[label]["escalations"] += 1
            disposition = str(details.get("new_state") or details.get("disposition") or event.get("state") or "").lower()
            if kind in {"disposition", "analyst_feedback"}:
                buckets[label]["dispositions"] += 1
                buckets[label]["false_positives"] += int(disposition in {"false_positive", "benign"})
        for review in reviews:
            label = bucket(review.get("created_at"))
            if label and review.get("new_state") in {"accepted", "rejected", "completed"}:
                buckets[label]["dispositions"] += 0
        for row in intelligence + reports:
            label = bucket(row.get("updated_at") or row.get("created_at"))
            if label:
                confidence = _number(_first(row, "confidence", "confidence_score", default=0))
                if confidence:
                    buckets[label]["confidence_sum"] += confidence
                    buckets[label]["confidence_samples"] += 1
        result = []
        for label in labels:
            item = buckets[label]
            providers = {}
            for provider, record in item.pop("providers").items():
                observations = record["observations"]
                providers[provider] = {"failure_rate": round(record["failures"] / observations, 4) if observations else 0.0, "unavailable_count": record["unavailable"], "average_latency": round(record["latency_sum"] / record["latency_samples"], 2) if record["latency_samples"] else 0.0}
            item["average_resolution_time"] = round(item["average_resolution_time"] / item.pop("resolution_samples"), 2) if item["resolution_samples"] else 0.0
            item["sla_compliance_rate"] = round(item.pop("sla_compliant") / item["sla_observed"], 4) if item["sla_observed"] else 0.0
            item["average_confidence"] = round(item.pop("confidence_sum") / item.pop("confidence_samples"), 4) if item["confidence_samples"] else 0.0
            item["provider_reliability"] = providers
            item["date"] = label
            result.append(item)
        return result

    @staticmethod
    def _trend_totals(trend):
        volume = sum(item["investigation_volume"] for item in trend)
        resolution = [item["average_resolution_time"] for item in trend if item["average_resolution_time"]]
        compliance = [item["sla_compliance_rate"] for item in trend if item["sla_observed"]]
        confidence = [item["average_confidence"] for item in trend if item["average_confidence"]]
        return {"investigation_volume": volume, "average_resolution_time": round(sum(resolution) / len(resolution), 2) if resolution else 0.0, "sla_compliance_rate": round(sum(compliance) / len(compliance), 4) if compliance else 0.0, "assignments": sum(item["assignments"] for item in trend), "escalations": sum(item["escalations"] for item in trend), "false_positives": sum(item["false_positives"] for item in trend), "dispositions": sum(item["dispositions"] for item in trend), "average_confidence": round(sum(confidence) / len(confidence), 4) if confidence else 0.0}

    @staticmethod
    def _analyst_metrics(lifecycle: list[dict[str, Any]], reviews: list[dict[str, Any]]) -> AnalystMetrics:
        assignments: dict[str, set[str]] = {}
        for row in lifecycle:
            if row.get("event_kind") == "assignment":
                details = row.get("details") or {}
                actor = str(details.get("assigned_to") or "")
                if actor: assignments.setdefault(actor, set()).add(str(row.get("case_id")))
        completed = [row for row in reviews if row.get("new_state") in {"accepted", "rejected", "completed"}]
        review_durations: list[float] = []
        review_history: dict[str, list[dict[str, Any]]] = {}
        for row in reviews:
            review_history.setdefault(str(row.get("evidence_id")), []).append(row)
        for history in review_history.values():
            terminal = next((row for row in reversed(history) if row.get("new_state") in {"accepted", "rejected", "completed"}), None)
            start = _time(history[0].get("created_at")) if history else None
            end = _time(terminal.get("created_at")) if terminal else None
            if start and end:
                review_durations.append(max(0.0, (end - start).total_seconds()))
        escalations = sum(1 for row in lifecycle if row.get("event_kind") == "escalation") + sum(1 for row in reviews if row.get("new_state") == "requires_escalation")
        false_positives = sum(1 for row in lifecycle if row.get("event_kind") in {"disposition", "analyst_feedback"} and str(row.get("state")) in {"false_positive", "benign"})
        dispositions = sum(1 for row in lifecycle if row.get("event_kind") in {"disposition", "analyst_feedback"})
        return AnalystMetrics(assigned_cases=sum(len(items) for items in assignments.values()), completed_reviews=len(completed), average_review_time=round(sum(review_durations) / len(review_durations), 2) if review_durations else 0.0, escalations=escalations, false_positive_rate=round(false_positives / dispositions, 4) if dispositions else 0.0, by_actor={actor: {"assigned_cases": len(cases)} for actor, cases in assignments.items()})

    @staticmethod
    def _provider_metrics(executions: list[dict[str, Any]]) -> ProviderMetrics:
        observations: dict[str, list[dict[str, Any]]] = {}
        for execution in executions:
            states = execution.get("provider_states") or execution.get("providers") or {}
            if isinstance(states, list):
                states = {str(item.get("provider")): item for item in states if isinstance(item, dict) and item.get("provider")}
            for provider, state in states.items():
                observations.setdefault(str(provider), []).append(state if isinstance(state, dict) else {"status": state})
        health, failures, unavailable, latency = {}, {}, {}, {}
        for provider, rows in observations.items():
            statuses = [str(_first(row, "status", "health_status", "availability_state", default="UNAVAILABLE")).upper() for row in rows]
            unavailable[provider] = sum(status in {"UNAVAILABLE", "FAILED", "BLOCKED"} for status in statuses)
            failures[provider] = round(sum(status in {"FAILED", "BLOCKED"} for status in statuses) / len(statuses), 4)
            health[provider] = "UNAVAILABLE" if unavailable[provider] else "HEALTHY"
            values = [_number(_first(row, "latency_ms", "latency", default=0)) for row in rows if _first(row, "latency_ms", "latency") is not None]
            latency[provider] = round(sum(values) / len(values), 2) if values else 0.0
        return ProviderMetrics(provider_health=health, failure_rate=failures, unavailable_count=unavailable, average_latency=latency)
