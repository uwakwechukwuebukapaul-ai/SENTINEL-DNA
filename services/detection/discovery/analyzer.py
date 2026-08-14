from .models import DetectionSuggestion
class DetectionDiscoveryEngine:
    def __init__(self): self.suggestions=[]
    def analyze(self, organization_id, anomalies):
        out=[]
        for a in anomalies:
            item=DetectionSuggestion(organization_id,"Suspicious Administrative Login Pattern",a.description,a.anomaly_type,{"event_type":a.anomaly_type},{"title":a.anomaly_type,"logsource":{"product":"any"},"detection":{"selection":{"event_type":a.anomaly_type}},"condition":"selection"},a.mitre_mapping,a.confidence,"GENERATED"); self.suggestions.append(item); out.append(item)
        return out
    def scoped(self, organization_id): return [x for x in self.suggestions if x.organization_id==organization_id]
