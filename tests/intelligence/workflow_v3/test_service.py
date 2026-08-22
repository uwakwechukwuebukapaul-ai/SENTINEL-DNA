from __future__ import annotations

from types import SimpleNamespace

from services.intelligence.workflow_v3 import AnalystWorkflowV3Service


class _Lifecycle:
    def __init__(self): self.events = []
    def list_for_case(self, case_id, *, tenant_id): return [item for item in self.events if item["case_id"] == case_id and item["tenant_id"] == tenant_id]
    def latest_sla(self, case_id, *, tenant_id): return next((item for item in reversed(self.list_for_case(case_id, tenant_id=tenant_id)) if item["event_kind"] == "sla"), None)
    def latest_escalation(self, case_id, *, tenant_id): return next((item for item in reversed(self.list_for_case(case_id, tenant_id=tenant_id)) if item["event_kind"] == "escalation"), None)
    def latest(self, case_id, *, tenant_id, event_kind=None): return next((item for item in reversed(self.list_for_case(case_id, tenant_id=tenant_id)) if event_kind is None or item["event_kind"] == event_kind), None)
    def assignments(self, case_id, *, tenant_id): return [item for item in self.list_for_case(case_id, tenant_id=tenant_id) if item["event_kind"] == "assignment"]
    def append(self, **kwargs):
        event = {"case_id": kwargs["case_id"], "tenant_id": kwargs["tenant_id"], "actor_id": kwargs["actor_id"], "event_kind": kwargs["event_kind"], "state": kwargs["state"], "details": kwargs.get("details", {}), "reason": kwargs.get("reason", "")}
        self.events.append(event); return event


class _Reports:
    def __init__(self, reports): self.reports = reports
    def page_for_tenant(self, tenant_id, *, page, page_size, status=None):
        items = [item for item in self.reports if item["tenant_context"]["tenant_id"] == tenant_id]
        if status: items = [item for item in items if item.get("status") == status]
        return {"items": items[(page - 1) * page_size: page * page_size], "page": page, "page_size": page_size, "total": len(items), "has_next": page * page_size < len(items)}


class _Coordinator:
    def __init__(self):
        self.report_repository = _Reports([{"case_id": "A", "title": "Critical case", "status": "in_progress", "confidence": .4, "risk_score": 95, "tenant_context": {"tenant_id": "T"}}])
        self.case_lifecycle_repository = _Lifecycle()
        self.assignment_directory = SimpleNamespace(validate_target=lambda **kwargs: kwargs)
        self.audit_service = SimpleNamespace(record=lambda *args, **kwargs: None)
    def get_investigation_view(self, case_id, context):
        if context.tenant_id != "T": raise PermissionError("investigation_not_found")
        return {"investigation": {"id": case_id, "status": "in_progress"}, "summary": {"title": "Critical case", "risk": 95, "confidence": .4}, "evidence": [{"evidence_id": "E-1", "confidence": .9}], "findings": [{"finding_id": "F-1", "evidence_refs": ["E-1"]}], "iocs": [{"evidence_refs": ["E-1"]}], "mitre": [{"evidence_refs": ["E-1"]}], "quality": {"overall_score": .5}, "provider_observations": [{"status": "AVAILABLE"}]}
    def get_investigation_explainability(self, case_id, context): return {"confidence_decomposition": {"components": {"evidence_quality": .5}}, "threat_intelligence": {"stale_indicators": [], "provider_agreement": {}}, "conclusion": {"contradicting_factors": []}}
    def get_contradictions(self, case_id, context): return {"items": []}
    def get_evidence_reviews(self, case_id, tenant_id): return []
    def get_feedback(self, case_id, tenant_id): return []
    def get_collaboration(self, case_id, tenant_id): return []
    def get_assignments(self, case_id, tenant_id): return self.case_lifecycle_repository.assignments(case_id, tenant_id=tenant_id)
    def get_audit_timeline(self, case_id, context): return []
    def get_report_by_case_id(self, case_id, tenant_id): return {"case_id": case_id} if tenant_id == "T" else None
    def assign_case(self, case_id, payload, *, tenant_id, actor_id): return self.case_lifecycle_repository.append(case_id=case_id, tenant_id=tenant_id, actor_id=actor_id, event_kind="assignment", state="case_owner", details={"assigned_to": payload["assignee_id"]})


def test_queue_is_deterministic_and_explains_priority():
    queue = AnalystWorkflowV3Service(_Coordinator()).queue("T")
    item = queue["items"][0]
    assert queue["version"] == "analyst-workflow-v3-queue-v1"
    assert item["priority_score"] >= 70
    assert "critical risk" in item["priority_reasons"]
    assert "low confidence" in item["priority_reasons"]


def test_evidence_priority_and_readiness_are_bounded():
    service = AnalystWorkflowV3Service(_Coordinator())
    priorities = service.evidence_priorities("A", "T")
    readiness = service.readiness("A", "T")
    assert priorities["items"][0]["evidence_id"] == "E-1"
    assert "linked to finding" in priorities["items"][0]["reasons"]
    assert 0 <= readiness["completion_percentage"] <= 100
    assert readiness["deterministic"] is True


def test_claim_and_release_are_append_only():
    coordinator = _Coordinator(); service = AnalystWorkflowV3Service(coordinator)
    service.claim("A", "T", "actor-a")
    service.release("A", "T", "actor-a", "handoff")
    assert [item["state"] for item in coordinator.case_lifecycle_repository.events] == ["case_owner", "released"]
