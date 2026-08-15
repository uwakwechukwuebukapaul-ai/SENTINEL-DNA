class AuditIntelligence:
    def summarize(self,readiness,drifts): return {"readiness_score":readiness.readiness_score,"drift_count":len(drifts),"requires_attention":bool(drifts) or readiness.readiness_score<.8}
