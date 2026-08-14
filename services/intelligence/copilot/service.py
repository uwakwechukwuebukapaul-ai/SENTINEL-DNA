from uuid import uuid4
from .context import CopilotContextBuilder
from .models import ConversationContext, CopilotRequest, CopilotResponse
from .reasoner import CopilotReasoner
from .repository import CopilotRepository

class SecurityCopilotService:
    def __init__(self, tenant_id=None, repository=None, audit_logger=None): self.tenant_id=tenant_id; self.repository=repository or CopilotRepository(); self.audit_logger=audit_logger; self.context_builder=CopilotContextBuilder(); self.reasoner=CopilotReasoner()
    def ask(self, question, investigation=None, **sources):
        context=self.context_builder.build(investigation, **sources); explanation=self.reasoner.answer(question, context); request=CopilotRequest(str(context.get("case_id") or "unknown"), question, context); response=CopilotResponse(request.case_id, explanation.conclusion, confidence=round(explanation.confidence*100), evidence_used=explanation.evidence_refs, evidence_refs=explanation.evidence_refs, metadata={"reasoning": explanation.to_dict(), "autonomous_actions": False}); self.repository.append(self.tenant_id, {"request": request.to_dict(), "response": response.to_dict()});
        if self.audit_logger and hasattr(self.audit_logger,"record"): self.audit_logger.record("copilot_interaction", tenant_id=self.tenant_id, case_id=request.case_id)
        return response
    def explain(self, investigation=None, **sources): return self.ask("Explain the incident and risk", investigation, **sources)
    def summarize(self, investigation=None, **sources): return self.ask("Summarize the evidence and intelligence", investigation, **sources)
    def recommend(self, investigation=None, **sources): return self.ask("Recommend safe investigation steps", investigation, **sources)
