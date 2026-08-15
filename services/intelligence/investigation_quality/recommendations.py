from .models import QualityRecommendation
class QualityRecommendationEngine:
    def generate(self, assessment):
        checks=(("evidence_score","evidence","low evidence coverage","Collect additional endpoint telemetry"),("enrichment_score","enrichment","IOC enrichment is incomplete","Correlate indicators with threat intelligence"),("mitre_mapping_score","mitre","ATT&CK mapping is incomplete","Improve ATT&CK technique mapping"),("confidence_score","confidence","Confidence is low or uncalibrated","Gather additional supporting evidence"),("timeline_score","timeline","Investigation timeline is incomplete","Review and complete event ordering"))
        return [QualityRecommendation(category,"high" if getattr(assessment, field)<40 else "medium",explanation,action) for field,category,explanation,action in checks if getattr(assessment,field)<70]
