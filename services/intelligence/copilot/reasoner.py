from .models import ReasoningExplanation
class CopilotReasoner:
    def answer(self, question, context):
        refs=[str(item.get("id") or item.get("evidence_id")) for item in context.get("evidence", []) if isinstance(item,dict) and (item.get("id") or item.get("evidence_id"))]
        return ReasoningExplanation(f"{question}: analysis is grounded in {len(refs)} evidence reference(s).", refs, ["Collect available evidence", "Compare threat and risk context", "Present analyst-verifiable conclusion"], .8 if refs else .3)
