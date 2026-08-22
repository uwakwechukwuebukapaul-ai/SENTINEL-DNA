"""Tenant-scoped, deterministic analyst workflow over canonical V2 boundaries."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any


class AnalystWorkflowV3Service:
    VERSION = "analyst-workflow-v3"
    WORKFLOW_STATES = ("NEW", "CLAIMED", "INVESTIGATING", "REVIEW_REQUIRED", "DECISION_READY", "APPROVAL_REQUIRED", "APPROVED", "REJECTED", "DISPOSITIONED", "CLOSED")

    def __init__(self, coordinator):
        self.coordinator = coordinator

    @staticmethod
    def _context(tenant_id: str):
        return SimpleNamespace(tenant_id=str(tenant_id))

    @staticmethod
    def _number(value, default=0.0):
        try:
            return float(value if value is not None else default)
        except (TypeError, ValueError):
            return float(default)

    def _item(self, report: dict[str, Any], tenant_id: str) -> dict[str, Any]:
        case_id = str(report.get("case_id"))
        context = self._context(tenant_id)
        view = self.coordinator.get_investigation_view(case_id, context) or {}
        summary = view.get("summary") or {}
        investigation = view.get("investigation") or {}
        explainability = self.coordinator.get_investigation_explainability(case_id, context) or {}
        contradictions = self.coordinator.get_contradictions(case_id, context) or {}
        lifecycle = self.coordinator.case_lifecycle_repository.list_for_case(case_id, tenant_id=str(tenant_id))
        assignments = [item for item in lifecycle if item.get("event_kind") == "assignment"]
        assignment = assignments[-1] if assignments else None
        sla = self.coordinator.case_lifecycle_repository.latest_sla(case_id, tenant_id=str(tenant_id)) or {}
        escalation = self.coordinator.case_lifecycle_repository.latest_escalation(case_id, tenant_id=str(tenant_id)) or {}
        approval = self.coordinator.case_lifecycle_repository.latest(case_id, tenant_id=str(tenant_id), event_kind="report_approval") or {}
        feedback = self.coordinator.get_feedback(case_id, str(tenant_id))
        reviews = self.coordinator.get_evidence_reviews(case_id, str(tenant_id))
        current_reviews = {}
        for review in reviews:
            current_reviews[str(review.get("evidence_id"))] = review
        quality = view.get("quality") or {}
        components = (explainability.get("confidence_decomposition") or {}).get("components") or {}
        unresolved = [item for item in contradictions.get("items", []) if item.get("analyst_review_state") not in {"resolved", "confirmed"}]
        intelligence = explainability.get("threat_intelligence") or {}
        stale = list(intelligence.get("stale_indicators") or [])
        provider_agreement = intelligence.get("provider_agreement") or {}
        assigned_to = (assignment.get("details") or {}).get("assigned_to") if assignment else None
        reasons: list[str] = []
        priority_score = 0
        risk = self._number(summary.get("risk", report.get("risk_score")))
        confidence = self._number(summary.get("confidence", report.get("confidence")))
        if risk >= 90: priority_score += 40; reasons.append("critical risk")
        elif risk >= 70: priority_score += 25; reasons.append("high risk")
        if sla.get("state") == "overdue": priority_score += 30; reasons.append("SLA breach")
        if unresolved: priority_score += 25; reasons.append("unresolved contradiction")
        if confidence < 0.6: priority_score += 20; reasons.append("low confidence")
        if stale: priority_score += 15; reasons.append("stale intelligence")
        if escalation: priority_score += 10; reasons.append("escalated")
        if not assigned_to: priority_score += 10; reasons.append("unassigned investigation")
        evidence_quality = self._number(components.get("evidence_quality", quality.get("overall_score", 0)), 0)
        if evidence_quality and evidence_quality < 0.6: priority_score += 10; reasons.append("low evidence quality")
        if unresolved:
            workflow_state = "REVIEW_REQUIRED"
        elif approval.get("state") == "approved":
            workflow_state = "APPROVED"
        elif approval.get("state") == "rejected":
            workflow_state = "REJECTED"
        elif feedback:
            workflow_state = "DISPOSITIONED"
        elif not assigned_to:
            workflow_state = "NEW"
        elif reviews:
            workflow_state = "INVESTIGATING"
        else:
            workflow_state = "CLAIMED"
        return {
            "investigation_id": str(investigation.get("id") or case_id), "case_id": case_id,
            "title": report.get("title") or summary.get("title") or case_id,
            "severity": str(report.get("severity") or "unknown").lower(), "risk": risk,
            "confidence": confidence, "status": investigation.get("status") or report.get("status") or "unknown",
            "workflow_state": workflow_state, "assigned_analyst": assigned_to,
            "sla_state": sla.get("state", "not_set"), "escalation_state": escalation.get("state", "not_escalated"),
            "contradiction_state": "unresolved" if unresolved else "clear", "contradiction_count": len(contradictions.get("items", [])),
            "evidence_quality": evidence_quality, "intelligence_freshness": "stale" if stale else "current",
            "provider_availability": "unavailable" if provider_agreement.get("unavailable_count") else "available",
            "mitre_present": bool(view.get("mitre")), "last_analyst_activity": (feedback[-1].get("created_at") if feedback else (reviews[-1].get("created_at") if reviews else None)),
            "created_at": investigation.get("created_at") or report.get("created_at"), "updated_at": report.get("updated_at"),
            "priority_score": min(100, priority_score), "priority": "critical" if priority_score >= 70 else "high" if priority_score >= 40 else "normal",
            "priority_reasons": reasons or ["routine evidence-backed review"], "reviewed_evidence": len(current_reviews),
        }

    def queue(self, tenant_id: str, *, page=1, page_size=25, filters=None) -> dict[str, Any]:
        filters = filters or {}
        base = self.coordinator.report_repository.page_for_tenant(tenant_id, page=page, page_size=page_size, status=filters.get("status"))
        items = [self._item(report, tenant_id) for report in base["items"]]
        for key in ("severity", "workflow_state", "sla_state", "escalation_state", "contradiction_state", "intelligence_freshness", "priority"):
            value = filters.get(key)
            if value: items = [item for item in items if str(item.get(key)) == str(value)]
        if filters.get("unassigned") in {True, "true", "1"}: items = [item for item in items if not item.get("assigned_analyst")]
        if filters.get("mitre") in {True, "true", "1"}: items = [item for item in items if item.get("mitre_present")]
        items.sort(key=lambda item: (-int(item["priority_score"]), str(item.get("updated_at") or ""), item["case_id"]))
        return {"version": self.VERSION + "-queue-v1", "items": items, "page": base["page"], "page_size": base["page_size"], "total": base["total"], "has_next": base["has_next"], "deterministic": True}

    def evidence_priorities(self, case_id: str, tenant_id: str) -> dict[str, Any]:
        context = self._context(tenant_id)
        view = self.coordinator.get_investigation_view(case_id, context)
        if view is None: raise LookupError("investigation_not_found")
        explainability = self.coordinator.get_investigation_explainability(case_id, context) or {}
        contradictions = self.coordinator.get_contradictions(case_id, context) or {}
        reviewed = {str(item.get("evidence_id")): item for item in self.coordinator.get_evidence_reviews(case_id, tenant_id)}
        finding_refs = {str(ref) for finding in view.get("findings", []) for ref in finding.get("evidence_refs", [])}
        ioc_refs = {str(ref) for ioc in view.get("iocs", []) for ref in ioc.get("evidence_refs", ioc.get("evidence_references", []))}
        mitre_refs = {str(ref) for item in view.get("mitre", []) for ref in item.get("evidence_refs", item.get("evidence_references", []))}
        contradiction_refs = {str(ref) for item in contradictions.get("items", []) for ref in (item.get("evidence_a"), item.get("evidence_b")) if ref}
        items = []
        for evidence in view.get("evidence", []):
            evidence_id = str(evidence.get("evidence_id") or evidence.get("id") or evidence.get("reference"))
            reasons, score = [], 0
            if evidence_id in finding_refs: score += 30; reasons.append("linked to finding")
            if evidence_id in ioc_refs: score += 20; reasons.append("linked to IOC")
            if evidence_id in mitre_refs: score += 15; reasons.append("supports ATT&CK technique")
            if evidence_id in contradiction_refs: score += 20; reasons.append("contradiction relevant")
            if evidence.get("confidence", 0) >= 0.8: score += 10; reasons.append("high evidence confidence")
            if evidence_id not in reviewed or reviewed[evidence_id].get("new_state") not in {"reviewed", "accepted", "completed"}: score += 10; reasons.append("not yet reviewed")
            items.append({"evidence_id": evidence_id, "priority_score": min(100, score), "priority": "high" if score >= 50 else "normal", "reasons": reasons or ["no elevated relationship"], "review_state": (reviewed.get(evidence_id) or {}).get("new_state", "pending_review"), "provenance": evidence.get("provenance", {})})
        items.sort(key=lambda item: (-item["priority_score"], item["evidence_id"]))
        return {"version": self.VERSION + "-evidence-priority-v1", "case_id": str(case_id), "items": items, "deterministic": True}

    def readiness(self, case_id: str, tenant_id: str) -> dict[str, Any]:
        context = self._context(tenant_id); view = self.coordinator.get_investigation_view(case_id, context)
        if view is None: raise LookupError("investigation_not_found")
        evidence = list(view.get("evidence", [])); reviews = self.coordinator.get_evidence_reviews(case_id, tenant_id)
        current = {str(item.get("evidence_id")): item for item in reviews}
        contradictions = self.coordinator.get_contradictions(case_id, context).get("items", [])
        unresolved = [item for item in contradictions if item.get("analyst_review_state") not in {"resolved", "confirmed"}]
        approval = self.coordinator.case_lifecycle_repository.latest(case_id, tenant_id=str(tenant_id), event_kind="report_approval") or {}
        feedback = self.coordinator.get_feedback(case_id, tenant_id)
        checks = {
            "evidence_reviewed": bool(evidence) and all((current.get(str(item.get("evidence_id"))) or {}).get("new_state") in {"reviewed", "accepted", "completed"} for item in evidence),
            "critical_evidence_reviewed": all((current.get(str(item.get("evidence_id"))) or {}).get("new_state") in {"reviewed", "accepted", "completed"} for item in evidence if float(item.get("confidence") or 0) >= 0.8),
            "threat_intelligence_available": bool(view.get("provider_observations")), "mitre_mapping_reviewed": bool(view.get("mitre")),
            "contradictions_resolved": not unresolved, "analyst_rationale_provided": bool(feedback), "decision_support_reviewed": bool(view.get("summary")),
            "approval_completed": approval.get("state") in {"approved", "rejected"} or not approval, "report_ready": bool(view.get("investigation")),
        }
        completed = [name for name, passed in checks.items() if passed]; blocking = ["evidence_reviewed" if not checks["evidence_reviewed"] else None, "contradictions_resolved" if unresolved else None, "analyst_rationale_provided" if not feedback else None, "approval_completed" if not checks["approval_completed"] else None]
        blocking = [item for item in blocking if item]
        return {"version": self.VERSION + "-readiness-v1", "case_id": str(case_id), "completion_percentage": round(len(completed) / len(checks) * 100, 2), "blocking_items": blocking, "warning_items": ["threat_intelligence_available" if not checks["threat_intelligence_available"] else None, "mitre_mapping_reviewed" if not checks["mitre_mapping_reviewed"] else None], "completed_items": completed, "checks": checks, "deterministic": True}

    def workflow(self, case_id: str, tenant_id: str) -> dict[str, Any]:
        item = next((value for value in self.queue(tenant_id, page=1, page_size=100)["items"] if value["case_id"] == str(case_id)), None)
        if item is None: raise LookupError("investigation_not_found")
        return {"version": self.VERSION + "-workflow-v1", "case_id": str(case_id), "workflow": item, "evidence_priorities": self.evidence_priorities(case_id, tenant_id), "readiness": self.readiness(case_id, tenant_id), "collaboration": self.coordinator.get_collaboration(case_id, tenant_id), "assignments": self.coordinator.get_assignments(case_id, tenant_id), "approval": self.coordinator.case_lifecycle_repository.latest(case_id, tenant_id=str(tenant_id), event_kind="report_approval"), "audit": self.coordinator.get_audit_timeline(case_id, self._context(tenant_id))}

    def claim(self, case_id: str, tenant_id: str, actor_id: str, reason=""):
        if self.coordinator.assignment_directory is None: raise PermissionError("assignment_directory_unavailable")
        self.coordinator.assignment_directory.validate_target(tenant_id=tenant_id, actor_id=actor_id)
        return self.coordinator.assign_case(case_id, {"assignee_id": actor_id, "assignment_type": "case_owner", "reason": reason or "Claimed by analyst"}, tenant_id=tenant_id, actor_id=actor_id)

    def release(self, case_id: str, tenant_id: str, actor_id: str, reason=""):
        if self.coordinator.get_report_by_case_id(case_id, tenant_id) is None: raise LookupError("investigation_not_found")
        event = self.coordinator.case_lifecycle_repository.append(case_id=case_id, investigation_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="assignment", state="released", reason=reason or "Released by analyst", details={"assigned_to": None, "assignment_type": "case_owner"})
        self.coordinator.audit_service.record("INVESTIGATION_ASSIGNMENT_RELEASED", case_id=str(case_id), user_id=str(actor_id), details={"tenant_id": str(tenant_id), "reason": reason or "Released by analyst"})
        return event
