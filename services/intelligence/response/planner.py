from uuid import uuid4
from .models import ResponsePlan
from .playbooks import actions_for

class ResponsePlanner:
    def create(self, tenant_id, investigation=None, risk_score=0.0, threat_classification=None, correlation=None, attack_paths=None):
        data = investigation.to_dict() if hasattr(investigation, "to_dict") else (investigation or {})
        text = str(threat_classification or data.get("threat_type") or data.get("summary") or "").lower()
        incident_type = "phishing" if "phish" in text else "credential_compromise" if "credential" in text else "malware" if "malware" in text else "suspicious_network" if "network" in text else "unknown"
        return ResponsePlan(str(uuid4()), tenant_id, incident_type, actions_for(incident_type), "Recommendations derived from investigation intelligence; human approval required", float(risk_score))
