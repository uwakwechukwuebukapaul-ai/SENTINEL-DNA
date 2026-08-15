class CopilotProvider:
    """Provider boundary; the default implementation is deterministic and local."""
    def generate(self,question,context):
        evidence=context.get("evidence",[]); refs=[str(x.get("id") or x.get("evidence_id")) for x in evidence if isinstance(x,dict) and (x.get("id") or x.get("evidence_id"))]
        if not refs: return {"answer":"Conclusion: Unknown. Available evidence is insufficient to support a confident conclusion.","confidence":None,"uncertainty":"Evidence is insufficient to support a confident conclusion. Human review is required.","evidence_refs":[],"reasoning":"No evidence references were available.","recommended_review":"Human analyst should review the relevant evidence sources."}
        return {"answer":f"Observed: {question} is supported by {len(refs)} available evidence reference(s).","confidence":context.get("confidence"),"uncertainty":"Additional source review may be required.","evidence_refs":refs,"reasoning":"Derived from the supplied workspace evidence without adding unsupported facts.","recommended_review":"Human analyst should verify the cited evidence and decide next steps."}
