class WorkflowAnalysis:
    def analyze(self, context):
        history=context.get("history", ()) if isinstance(context,dict) else ()
        return {"transitions":tuple(context.get("transitions",())) if history else (), "complexity":("review evidence dependencies",) if history else (), "confidence":"moderate" if history else "insufficient_history"}
