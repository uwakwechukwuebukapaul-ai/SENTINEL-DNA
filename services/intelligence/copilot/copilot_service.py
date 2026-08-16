from .context_builder import CopilotContextBuilder
from .copilot_engine import GovernedCopilotEngine
from typing import Any

class InvestigationCopilot:
    """Legacy deterministic assistance over canonical intelligence snapshots."""
    def explain(self, intelligence: dict[str, Any]) -> str:
        findings = "; ".join(str(item) for item in intelligence.get("findings", [])[:3]) or "No findings recorded."
        return f"Risk is {intelligence.get('risk_score', 0)} ({intelligence.get('risk_severity', 'unknown')}) with {float(intelligence.get('confidence', 0)):.0%} confidence. Findings: {findings}"
    def summarize_attack_story(self, intelligence): return str(intelligence.get("attack_story") or "No attack story has been recorded for this investigation.")
    def suggest_actions(self, intelligence): return list(intelligence.get("recommendations", [])) or ["Validate the highest-risk indicators and preserve supporting evidence.", "Review the investigation timeline with the case owner."]
    def questions(self, intelligence): return [f"What evidence supports the {intelligence.get('risk_severity', 'current')} risk assessment?", "Which MITRE techniques are confirmed versus suspected?", "What is the next containment or validation step?"]
    def answer(self,prompt,intelligence):
        key=(prompt or "explain").strip().lower(); result=self.summarize_attack_story(intelligence) if key in {"attack story","summarize","summary"} else self.suggest_actions(intelligence) if key in {"actions","next actions","recommendations"} else self.questions(intelligence) if key in {"questions","investigation questions"} else self.explain(intelligence); return {"prompt":prompt,"result":result}
    def ai_answer(self,prompt,intelligence,fabric=None,organization_id=None): return self.answer(prompt,intelligence) if fabric is None or not organization_id else {"prompt":prompt,"result":fabric.investigate(organization_id,prompt,intelligence.get("evidence",[]))}
class GovernedCopilotService:
    def __init__(self,builder=None,engine=None): self.builder=builder or CopilotContextBuilder();self.engine=engine or GovernedCopilotEngine()
    def context(self,tenant_id,case_id,**sources): return self.builder.build(tenant_id,case_id,**sources).to_dict()
    def reason(self,tenant_id,case_id,**sources): return self.engine.run(self.builder.build(tenant_id,case_id,**sources))
    def explain(self,tenant_id,case_id,**sources): return self.reason(tenant_id,case_id,**sources)['explanation']
    def recommend(self,tenant_id,case_id,**sources): return self.reason(tenant_id,case_id,**sources)['recommendations']
