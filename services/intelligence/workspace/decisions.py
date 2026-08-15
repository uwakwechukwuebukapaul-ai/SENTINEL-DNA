class WorkspaceDecisionSurface:
    def build(self,items):
        return [{"priority":x.get("priority","medium"),"source":x.get("source_subsystem",x.get("source","unknown")),"rationale":x.get("rationale",""),"confidence":x.get("confidence"),"evidence_references":x.get("evidence_references",[]),"provenance":x.get("provenance",{}),"advisory":True,"requires_human_review":True} for x in (items or [])]
