from .models import InvestigationStepRecommendation

class InvestigationPlanAdvisor:
    ORDER=("collect_evidence", "enrich_iocs", "map_threat_intelligence", "reason_over_graph", "assess_risk", "document_findings")
    def recommend(self, steps):
        supplied=[str(step) for step in steps]; ordered=sorted(supplied, key=lambda step: self.ORDER.index(step) if step in self.ORDER else len(self.ORDER)); return [InvestigationStepRecommendation(step, index, "Evidence and enrichment should precede reasoning and risk assessment") for index, step in enumerate(ordered,1)]
