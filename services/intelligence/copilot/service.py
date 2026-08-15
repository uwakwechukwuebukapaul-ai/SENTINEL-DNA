from uuid import uuid4
from .context import CopilotContextBuilder
from .models import ConversationContext, CopilotRequest, CopilotResponse
from .reasoner import CopilotReasoner
from .repository import CopilotRepository
from .provider import CopilotProvider

class SecurityCopilotService:
    def __init__(self, tenant_id=None, repository=None, audit_logger=None, provider=None): self.tenant_id=tenant_id; self.repository=repository or CopilotRepository(); self.audit_logger=audit_logger; self.context_builder=CopilotContextBuilder(); self.reasoner=CopilotReasoner(); self.provider=provider or CopilotProvider()
    def ask(self, question, investigation=None, **sources):
        context=self.context_builder.build(investigation, **sources); explanation=self.reasoner.answer(question, context); request=CopilotRequest(str(context.get("case_id") or "unknown"), question, context); response=CopilotResponse(request.case_id, explanation.conclusion, confidence=round(explanation.confidence*100), evidence_used=explanation.evidence_refs, evidence_refs=explanation.evidence_refs, metadata={"reasoning": explanation.to_dict(), "autonomous_actions": False}); self.repository.append(self.tenant_id, {"request": request.to_dict(), "response": response.to_dict()});
        if self.audit_logger and hasattr(self.audit_logger,"record"): self.audit_logger.record("copilot_interaction", tenant_id=self.tenant_id, case_id=request.case_id)
        return response
    def explain(self, investigation=None, **sources): return self.ask("Explain the incident and risk", investigation, **sources)
    def summarize(self, investigation=None, **sources): return self.ask("Summarize the evidence and intelligence", investigation, **sources)
    def recommend(self, investigation=None, **sources): return self.ask("Recommend safe investigation steps", investigation, **sources)
    def _workspace(self,workspace_context):
        if workspace_context is None: return {"evidence":[],"confidence":None,"provenance":[]}
        data=workspace_context.to_dict() if hasattr(workspace_context,"to_dict") else dict(workspace_context)
        if data.get("tenant_id") not in {None,self.tenant_id}: raise PermissionError("workspace tenant does not match Copilot tenant")
        return {"evidence":data.get("evidence",[]),"confidence":data.get("investigation",{}).get("confidence"),"provenance":data.get("fabric",{}).get("provenance",[]) if isinstance(data.get("fabric"),dict) else []}
    def answer_question(self,question,workspace_context=None):
        context=self._workspace(workspace_context); result=self.provider.generate(question,context); refs=result.get("evidence_refs",[]); response=CopilotResponse(str((workspace_context or {}).get("case_id","unknown") if isinstance(workspace_context,dict) else "unknown"),result["answer"],confidence=int(result["confidence"]*100) if isinstance(result.get("confidence"),(int,float)) else 0,evidence_used=refs,evidence_refs=refs,uncertainty=result.get("uncertainty", "Confidence: unavailable"),provenance=context.get("provenance",[]),metadata={"reasoning":result.get("reasoning"),"recommended_review":result.get("recommended_review"),"autonomous_actions":False}); self._audit("copilot_answer_generated",case_id=response.case_id); return response
    def summarize_investigation(self,workspace_context): return self.answer_question("Summarize this investigation",workspace_context)
    def explain_finding(self,finding,workspace_context=None): return self.answer_question(f"Explain finding {finding}",workspace_context)
    def explain_risk(self,workspace_context=None): return self.answer_question("Why is this case high risk?",workspace_context)
    def explain_recommendation(self,recommendation,workspace_context=None): return self.answer_question(f"Why was this recommendation generated: {recommendation}",workspace_context)
    def explain_evidence(self,workspace_context=None): return self.answer_question("What evidence supports this conclusion?",workspace_context)
    def explain_timeline(self,workspace_context=None): return self.answer_question("What happened on the timeline?",workspace_context)
    def prepare_review_context(self,workspace_context):
        self._audit("copilot_context_prepared"); return {"context":self._workspace(workspace_context),"advisory":True,"requires_human_review":True,"tts_enabled":False}
    def _audit(self,event,**payload):
        if self.audit_logger and hasattr(self.audit_logger,"record"): self.audit_logger.record(event,tenant_id=self.tenant_id,**payload)
