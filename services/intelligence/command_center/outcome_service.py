from .outcome import InvestigationOutcome, stable_outcome_id

class InvestigationOutcomeService:
    """Derives an outcome view from the existing workspace without mutating it."""
    def __init__(self, workspace_service=None): self.workspace_service=workspace_service
    def derive(self, workspace):
        if not workspace: return None
        investigation=workspace.investigation; iid=str(investigation.get("investigation_id", "")); evidence=list(workspace.evidence or []); decision=workspace.decision or {}; events=list(workspace.events or [])
        refs=[x.get("evidence_id",x.get("id")) for x in evidence if x.get("status")!="unavailable"]
        missing=[x.get("evidence_id",x.get("id")) for x in evidence if x.get("status")=="unavailable"]
        uncertainty=list(workspace.uncertainty and [workspace.uncertainty] or [])
        unresolved=list(missing)
        if decision and decision.get("decision_state") not in {"completed_reference","unknown"}:
            unresolved.append("decision_pending")
            uncertainty.append("decision_unresolved")
        confidences=[x.get("confidence") for x in [investigation,decision] + events if isinstance(x,dict) and isinstance(x.get("confidence"),(int,float))]
        confidence=min(confidences) if confidences else None
        if confidence is not None and confidence < .7: uncertainty.append("low_confidence")
        explicit=investigation.get("outcome_category") or investigation.get("outcome") or investigation.get("verdict")
        supported=bool(refs) and not missing and not uncertainty and (confidence is None or confidence >= .7)
        if not supported:
            category="insufficient_evidence" if missing or not refs else "requires_human_review"
            unresolved.append("additional_human_review")
        elif explicit in {"confirmed_threat","likely_threat","suspicious","benign","false_positive","inconclusive"}:
            category=explicit
        else:
            category="inconclusive"; unresolved.append("outcome_classification")
        review=bool(workspace.requires_human_review or unresolved or category in {"requires_human_review","insufficient_evidence","inconclusive"})
        uncertainty=list(dict.fromkeys(str(x) for x in uncertainty if x)); unresolved=list(dict.fromkeys(str(x) for x in unresolved if x))
        return InvestigationOutcome(iid,workspace.tenant_id,stable_outcome_id(workspace.tenant_id,iid),category,"analytical",confidence,uncertainty,refs,[decision.get("decision_context_id")] if decision else [],[x.get("event_id") for x in events],unresolved,review,workspace.provenance,True)
    def get_outcome(self, tenant_id, investigation_id):
        workspace=self.workspace_service.build(tenant_id,investigation_id) if self.workspace_service else None
        return self.derive(workspace) if workspace else None
