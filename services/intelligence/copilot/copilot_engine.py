from .reasoning import CopilotReasoningEngine
class GovernedCopilotEngine:
    def __init__(self): self.reasoning=CopilotReasoningEngine()
    def run(self,context): return self.reasoning.reason(context)

class InvestigationCopilot:
    """Compatibility adapter used by InvestigationCoordinator; advisory only."""
    def __init__(self, ai_runtime=None): self.ai_runtime=ai_runtime
    @staticmethod
    def _data(value):
        if value is None:return {}
        if hasattr(value,'to_dict'):return dict(value.to_dict())
        if hasattr(value,'snapshot'):return dict(value.snapshot())
        return dict(value) if isinstance(value,dict) else dict(vars(value))
    def _answer(self,context,result,reasoning_report,decision_report,memory_reference,question,prompt):
        from .models import CopilotResponse
        from .prompts import build_summary_prompt,build_reasoning_prompt,build_recommendation_prompt
        ctx,res,reasoning,decision=map(self._data,(context,result,reasoning_report,decision_report));findings=reasoning.get('findings',[]) or [];answer=reasoning.get('summary') or decision.get('rationale') or 'No evidence-backed conclusion is available.';refs=[str(x.get('id') or x.get('evidence_id')) for x in ctx.get('evidence',[]) if isinstance(x,dict)]
        if 'mitre' in question.lower(): answer='MITRE techniques involved: '+', '.join(res.get('mitre',[]) or reasoning.get('mitre_techniques',[]) or ['none identified'])
        quality = res.get('metadata', {}).get('quality_assessment', {}) if isinstance(res.get('metadata'), dict) else {}
        quality_context = {key: quality.get(key) for key in ('overall_score', 'evidence_score', 'confidence_score', 'quality_status') if quality.get(key) is not None}
        return CopilotResponse(case_id=str(ctx.get('case_id') or res.get('case_id') or 'unknown'),answer=answer,confidence=int(float(res.get('confidence') or reasoning.get('confidence') or 0)*100),evidence_used=refs,evidence_refs=refs,reasoning_refs=[str(f.get('finding_id')) for f in findings if isinstance(f,dict)],recommended_actions=list(res.get('recommendations',[]) or decision.get('recommended_actions',[]) or []),mitre_techniques=list(res.get('mitre',[]) or []),metadata={'synthetic_only':True,'provider':'deterministic_copilot','prompt':prompt,'finding_count':len(findings),'quality_assessment':quality_context})
    def answer_read_model(self, question, read_model):
        """Answer from the sanitized read model; feedback remains evaluation data."""
        from .models import CopilotResponse
        view = self._data(read_model)
        investigation = view.get("investigation", {})
        summary = view.get("summary", {})
        findings = view.get("findings", []) or []
        evidence = view.get("evidence", []) or []
        answer = summary.get("decision") or summary.get("title") or "No evidence-backed conclusion is available."
        if "finding" in question.lower() and findings:
            answer = "; ".join(str(item.get("finding", "")) for item in findings[:5])
        refs = [str(item.get("evidence_id") or item.get("id") or item.get("reference")) for item in evidence if isinstance(item, dict)]
        return CopilotResponse(case_id=str(investigation.get("case_id", "unknown")), answer=answer, confidence=int(float(summary.get("confidence") or 0) * 100), evidence_used=refs, evidence_refs=refs, reasoning_refs=[str(item.get("finding_id")) for item in findings if isinstance(item, dict) and item.get("finding_id")], recommended_actions=[item.get("recommendation", item) for item in view.get("recommendations", [])], mitre_techniques=list(view.get("mitre", []) or []), metadata={"synthetic_only": True, "provider": "deterministic_copilot", "prompt": question, "finding_count": len(findings), "quality_assessment": view.get("quality", {})})
    def summarize_investigation(self,context,result,reasoning_report=None,decision_report=None,memory_reference=None):return self._answer(context,result,reasoning_report,decision_report,memory_reference,'What happened?','summary')
    def answer_question(self,question,context,result,reasoning_report=None,decision_report=None,memory_reference=None):return self._answer(context,result,reasoning_report,decision_report,memory_reference,question,question)
    def recommend_next_steps(self,context,result,reasoning_report=None,decision_report=None,memory_reference=None):return self._answer(context,result,reasoning_report,decision_report,memory_reference,'What should I investigate next?','recommendation')
