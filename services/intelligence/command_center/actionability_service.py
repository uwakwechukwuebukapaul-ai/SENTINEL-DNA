from .actionability import AnalystNextStep, stable_step_id

class AnalystActionabilityService:
    """Derives stable, non-executable recommendations from an existing workspace."""
    def __init__(self, workspace_service=None): self.workspace_service = workspace_service

    def _step(self, workspace, category, title, description, reason, priority, refs, nav, confidence=None, uncertainty="", review=True):
        return AnalystNextStep(stable_step_id(workspace.tenant_id, workspace.investigation.get("investigation_id", ""), category), workspace.tenant_id, workspace.investigation.get("investigation_id", ""), title, description, reason, category, priority, "recommended", list(dict.fromkeys(refs)), nav, confidence, uncertainty, review, True)

    def derive(self, workspace):
        if not workspace: return []
        inv=workspace.investigation; iid=str(inv.get("investigation_id", "")); steps=[]
        evidence=list(workspace.evidence or []); missing=[x for x in evidence if x.get("status")=="unavailable"]
        attention=workspace.attention or {}; events=list(workspace.events or []); decision=workspace.decision or {}
        if missing:
            steps.append(self._step(workspace,"missing_evidence","Gather additional evidence","Review unavailable evidence references before drawing a conclusion.","missing_evidence","high",[x.get("evidence_id") for x in missing],workspace.navigation.get("evidence",[]),decision.get("confidence"),"evidence_unavailable",True))
        if attention.get("priority") in {"critical","high"}:
            steps.append(self._step(workspace,"high_attention","Review high-priority attention","Review the attention item and its supporting context first.","high_attention", "high",[attention.get("attention_id")],workspace.navigation.get("attention",{}),attention.get("confidence"),attention.get("uncertainty", ""),True))
        if decision and decision.get("decision_state") not in {"completed_reference","unknown"}:
            steps.append(self._step(workspace,"unresolved_decision","Review decision context","Review the open decision question and its evidence before deciding.","unresolved_decision","high",[decision.get("decision_context_id")],workspace.navigation.get("decision",{}),decision.get("confidence"),"" if not decision.get("uncertainty") else "decision_uncertain",True))
        confidences=[x.get("confidence") for x in events+[inv,decision] if isinstance(x,dict) and isinstance(x.get("confidence"),(int,float))]
        low=min(confidences) if confidences and min(confidences)<0.7 else None
        if low is not None:
            steps.append(self._step(workspace,"low_confidence","Validate low-confidence context","Validate the supporting context before relying on this investigation view.","low_confidence","medium",[iid],workspace.navigation.get("investigation",{}),low,"confidence_limited",True))
        if events:
            steps.append(self._step(workspace,"related_events_available","Compare related events","Review the related event timeline for corroborating changes.","related_events_available","medium",[x.get("event_id") for x in events],workspace.navigation.get("events",[]),None,"",workspace.requires_human_review))
        if workspace.requires_human_review:
            steps.append(self._step(workspace,"human_review_required","Escalate for human review","A human analyst must review the evidence and context before consequential action.","human_review_required","high",[iid],workspace.navigation.get("investigation",{}),None,workspace.uncertainty,True))
        if not steps:
            steps.append(self._step(workspace,"investigation_context_available","Review investigation context","Review the available investigation context and authoritative references.","investigation_context_available","low",[iid],workspace.navigation.get("investigation",{}),None,workspace.uncertainty,True))
        order={"missing_evidence":0,"high_attention":1,"unresolved_decision":2,"low_confidence":3,"human_review_required":4,"related_events_available":5,"investigation_context_available":6}
        return sorted(steps,key=lambda x:(order.get(x.category,99),x.step_id))

    def get_next_steps(self, tenant_id, investigation_id):
        workspace=self.workspace_service.build(tenant_id,investigation_id) if self.workspace_service else None
        if not workspace: return None
        steps=self.derive(workspace); confidences=[x.confidence for x in steps if x.confidence is not None]
        return {"investigation_id":str(investigation_id),"tenant_id":tenant_id,"next_steps":[x.to_dict() for x in steps],"requires_human_review":workspace.requires_human_review,"confidence":min(confidences) if confidences else None,"uncertainty":([workspace.uncertainty] if workspace.uncertainty else [x.uncertainty for x in steps if x.uncertainty]),"provenance":workspace.provenance,"advisory_only":True}
