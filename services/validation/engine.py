from .models import ValidationResult
class ValidationEngine:
    def __init__(self): self.results = {}
    def run(self, campaign_result):
        campaign = campaign_result.get("campaign") or {}; stages = campaign.get("stages") or []; expected = {str(s.get("technique_id")) for s in stages if s.get("technique_id")}
        detections = campaign_result.get("detections") or campaign_result.get("alerts") or []; detected = {str(a.get("technique_id")) for a in detections if a.get("technique_id")}; detected &= expected
        missed = sorted(expected - detected); tactic = {}
        for stage in stages:
            name = stage.get("tactic", "Unknown"); entry = tactic.setdefault(name, {"expected": 0, "detected": 0}); entry["expected"] += 1; entry["detected"] += int(str(stage.get("technique_id")) in detected)
        tactic = {key: {**value, "coverage": round(value["detected"] / value["expected"] * 100, 2) if value["expected"] else 0} for key, value in tactic.items()}
        coverage = round(len(detected) / len(expected) * 100, 2) if expected else 0
        gaps = [{"technique_id": technique, "detection_gap": "No matching alert was generated", "recommended_sigma_rule": {"title": f"Coverage for {technique}", "technique_id": technique, "logsource": {"product": "enterprise"}, "detection": {"selection": {"technique_id": technique}, "condition": "selection"}}, "recommendation": "Add telemetry mapping, a Sigma rule, and regression coverage."} for technique in missed]
        scores = {"detection": coverage, "investigation": 100.0 if campaign_result.get("investigation_id") or campaign_result.get("investigation") else (50.0 if detected else 0.0), "response": 100.0 if campaign_result.get("response") or campaign_result.get("soar") else 0.0, "automation": 100.0 if campaign_result.get("automation") or campaign_result.get("playbook") else 0.0}
        scores["overall_security_posture"] = round(sum(scores.values()) / 4, 2)
        result = ValidationResult(campaign.get("id", campaign_result.get("campaign_id", "unknown")), sorted(detected), missed, {"expected": len(expected), "detected": len(detected), "coverage": coverage}, tactic, scores, gaps); self.results[result.id] = result; return result
