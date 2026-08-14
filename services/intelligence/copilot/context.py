class CopilotContextBuilder:
    def build(self, investigation=None, **sources):
        data=investigation.to_dict() if hasattr(investigation,"to_dict") else (investigation or {})
        return {"evidence": data.get("evidence", data.get("artifacts", [])), "iocs": data.get("iocs", data.get("indicators", [])), "threat_intelligence": sources.get("threat_intelligence", data.get("threat_intelligence_report")), "attack_paths": sources.get("attack_paths", data.get("attack_path_context")), "exposure": sources.get("exposure", data.get("exposure_management_context")), "posture": sources.get("posture", data.get("security_posture_context")), "incident": sources.get("incident", data.get("incident_management_context")), "case_id": data.get("case_id")}
