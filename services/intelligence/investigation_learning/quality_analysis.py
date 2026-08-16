class QualityAnalysis:
    def analyze(self, context):
        history = context.get("history", ()) if isinstance(context, dict) else ()
        return {"quality_trend": "observed trends require review" if history else "insufficient_history", "advisory_only": True}
