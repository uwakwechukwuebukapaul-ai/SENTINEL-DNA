class EffectivenessMetrics:
    def calculate(self, expected=0, detected=0, false_positives=0, mttd=0, mttr=0, ai_quality=0, automation=0):
        return {"detection_rate": round(detected / expected * 100, 2) if expected else 0, "false_positives": false_positives, "MTTD": mttd, "MTTR": mttr, "ai_investigation_quality": ai_quality, "automation_effectiveness": automation}
