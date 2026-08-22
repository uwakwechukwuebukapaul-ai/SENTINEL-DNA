"""Stable, redacted compliance export projection for investigations."""
from __future__ import annotations
from datetime import datetime, timezone

SCHEMA_VERSION = "compliance-export-v1"


class ComplianceExportBuilder:
    def build(self, coordinator, case_id: str, security_context):
        tenant_id = getattr(security_context, "tenant_id", None)
        if not tenant_id:
            raise PermissionError("investigation tenant authorization is required")
        view = coordinator.get_investigation_view(case_id, security_context)
        if not view:
            return None
        report = coordinator.get_report_by_case_id(case_id, str(tenant_id)) or {}
        intelligence = coordinator.intelligence_repository.get_by_case_id(case_id) or {}
        executions = coordinator.execution_repository.list_for_case(case_id, tenant_id=str(tenant_id))
        evidence_reviews = coordinator.evidence_review_repository.list_for_case(case_id, tenant_id=str(tenant_id))
        lifecycle = coordinator.case_lifecycle_repository.list_for_case(case_id, tenant_id=str(tenant_id))
        assignments = coordinator.case_lifecycle_repository.assignments(case_id, tenant_id=str(tenant_id))
        sla = coordinator.case_lifecycle_repository.latest_sla(case_id, tenant_id=str(tenant_id))
        escalation = coordinator.case_lifecycle_repository.latest_escalation(case_id, tenant_id=str(tenant_id))
        collaboration = coordinator.get_collaboration(case_id, str(tenant_id))
        feedback = coordinator.get_feedback(case_id, str(tenant_id))
        return {
            "schema_version": SCHEMA_VERSION,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "investigation": view.get("investigation", {}),
            "alert": report.get("alert") or view.get("summary", {}),
            "evidence_references": view.get("evidence", []),
            "evidence_review_history": evidence_reviews,
            "ioc_enrichment_history": view.get("iocs", []),
            "threat_intelligence_observations": view.get("provider_observations", []),
            "provider_health_states": [item for execution in executions for item in execution.get("provider_states", []) or []],
            "reasoning_claims": [item for item in view.get("findings", []) if item.get("evidence_refs")],
            "mitre_attack_mappings": view.get("mitre", []),
            "decisions": [{"decision": item.get("decision"), "disposition": item.get("disposition"), "evidence_refs": item.get("evidence_refs", []), "actor_id": item.get("analyst_id"), "timestamp": item.get("created_at")} for item in feedback],
            "analyst_actions": collaboration,
            "collaboration_history": collaboration,
            "disposition_lifecycle": feedback,
            "case_lifecycle": lifecycle,
            "assignment_history": assignments,
            "sla": sla,
            "escalation": escalation,
            "execution_history": executions,
            "analyst_approvals": [item for item in lifecycle if item.get("event_kind") == "report_approval"],
            "audit_timeline": coordinator.get_audit_timeline(case_id, security_context),
            "report_provenance": {"schema_version": (report.get("metadata") or {}).get("schema_version", "investigation-report-v1"), "generated_at": (report.get("metadata") or {}).get("generated_at"), "generated_by": (report.get("metadata") or {}).get("generated_by")},
        }
