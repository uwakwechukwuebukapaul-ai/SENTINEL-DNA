from .feedback import AnalystInvestigationFeedback, InvestigationQualitySignal, AGREEMENT, EVIDENCE, USEFULNESS, stable_feedback_id

class FeedbackRepository:
    def __init__(self): self.items={}
    def save(self, item): self.items.setdefault((item.tenant_id,item.investigation_id),[]).append(item); return item
    def list(self, tenant_id, investigation_id): return list(self.items.get((tenant_id,str(investigation_id)),[]))
    def list_tenant(self, tenant_id): return [x for (tenant,_), values in self.items.items() if tenant==tenant_id for x in values]

class InvestigationFeedbackService:
    def __init__(self, workspace_service=None, outcome_service=None, repository=None):
        self.workspace_service=workspace_service; self.outcome_service=outcome_service; self.repository=repository or FeedbackRepository()
    def _context(self, tenant_id, investigation_id):
        workspace=self.workspace_service.build(tenant_id,str(investigation_id)) if self.workspace_service else None
        if not workspace: return None, None
        return workspace, self.outcome_service.derive(workspace) if self.outcome_service else None
    def submit(self, tenant_id, investigation_id, payload):
        workspace,outcome=self._context(tenant_id,investigation_id)
        if not workspace: return None
        if not isinstance(payload,dict): raise ValueError("invalid_feedback")
        allowed={"outcome_agreement","evidence_sufficiency","recommendation_usefulness","confidence","reason_codes","supporting_references","analyst_reference"}
        if set(payload)-allowed: raise ValueError("invalid_feedback_fields")
        if not isinstance(investigation_id,str) or not investigation_id or len(investigation_id)>200: raise ValueError("invalid_investigation_id")
        required={"outcome_agreement","evidence_sufficiency","recommendation_usefulness"}
        if not required.issubset(payload): raise ValueError("missing_feedback_fields")
        agreement=payload["outcome_agreement"]; evidence=payload["evidence_sufficiency"]; useful=payload["recommendation_usefulness"]
        if agreement not in AGREEMENT or evidence not in EVIDENCE or useful not in USEFULNESS: raise ValueError("invalid_feedback_category")
        confidence=payload.get("confidence")
        if confidence is not None and (not isinstance(confidence,(int,float)) or not 0 <= confidence <= 1): raise ValueError("invalid_feedback_confidence")
        for key in ("reason_codes","supporting_references"):
            if key in payload and (not isinstance(payload[key],list) or any(not isinstance(x,str) or len(x)>200 for x in payload[key])): raise ValueError("invalid_feedback_references")
        analyst=payload.get("analyst_reference","")
        if not isinstance(analyst,str) or len(analyst)>200: raise ValueError("invalid_feedback_analyst")
        existing=self.repository.list(tenant_id,investigation_id)
        item=AnalystInvestigationFeedback(stable_feedback_id(tenant_id,str(investigation_id),len(existing)),tenant_id,str(investigation_id),outcome.outcome_id if outcome else "",analyst,agreement,evidence,useful,confidence,list(payload.get("reason_codes",[])),list(payload.get("supporting_references",[])),workspace.provenance)
        return self.repository.save(item)
    def quality(self, tenant_id, investigation_id):
        workspace,outcome=self._context(tenant_id,investigation_id)
        if not workspace: return None
        feedback=self.repository.list(tenant_id,investigation_id)
        if not feedback: return InvestigationQualitySignal("insufficient_data",{"outcome_agreement":"unknown","evidence_sufficiency":"unknown","recommendation_usefulness":"unknown"},["no_analyst_feedback"],0,["analyst_assessment_unavailable"],True,workspace.provenance)
        latest=feedback[-1]; agreements={x.outcome_agreement for x in feedback}; dimensions={"outcome_agreement":("conflicting" if len(agreements)>1 else latest.outcome_agreement),"evidence_sufficiency":latest.evidence_sufficiency,"recommendation_usefulness":latest.recommendation_usefulness}; reasons=[]; uncertainty=[]
        if len(agreements)>1: reasons.append("analyst_feedback_conflicted"); uncertainty.append("conflicting_feedback")
        if latest.outcome_agreement=="disagree": reasons.append("analyst_disagreed_with_investigation_outcome")
        if latest.evidence_sufficiency in {"insufficient","partially_sufficient"}: reasons.append("supporting_evidence_was_incomplete")
        if latest.recommendation_usefulness=="not_useful": reasons.append("recommendations_were_not_useful")
        if latest.outcome_agreement=="unable_to_assess" or latest.evidence_sufficiency=="unable_to_assess": uncertainty.append("assessment_incomplete")
        status="needs_review" if reasons or uncertainty else "acceptable"
        provenance={"workspace":latest.provenance,"feedback_ids":[x.feedback_id for x in feedback],"outcome_reference":latest.outcome_reference}
        return InvestigationQualitySignal(status,dimensions,reasons,len(feedback),uncertainty,True,provenance)
    def get(self, tenant_id, investigation_id):
        workspace,outcome=self._context(tenant_id,investigation_id)
        if not workspace: return None
        return {"investigation_id":str(investigation_id),"feedback":[x.to_dict() for x in self.repository.list(tenant_id,investigation_id)],"quality":self.quality(tenant_id,investigation_id).to_dict(),"advisory_only":True,"provenance":workspace.provenance}
    def list_feedback(self, tenant_id): return self.repository.list_tenant(tenant_id)
