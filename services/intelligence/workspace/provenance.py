class WorkspaceProvenance:
    def collect(self,context):
        return [x.get("provenance",x.get("source",{})) for x in context.evidence if isinstance(x,dict) and (x.get("provenance") or x.get("source"))]
