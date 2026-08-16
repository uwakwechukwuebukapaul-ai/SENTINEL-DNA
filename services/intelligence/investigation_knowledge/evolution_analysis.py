class EvolutionAnalysis:
    def analyze(self, context):
        history=context.get("history", ()) if isinstance(context,dict) else ()
        return {"maturity":"developing" if history else "insufficient_history", "trends":("available evidence indicates reusable insight candidates",) if history else (), "confidence":"moderate" if history else "insufficient_history"}
