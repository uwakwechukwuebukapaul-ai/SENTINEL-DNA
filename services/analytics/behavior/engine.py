from .models import BehaviorFinding

class BehaviorEngine:
    def analyze(self, event):
        data = event.normalized_event or event.raw_event or {}; reasons = []; techniques = []
        hour = data.get("hour")
        if hour is not None and (int(hour) < 6 or int(hour) > 22): reasons.append("unusual login time"); techniques.append("T1078")
        if data.get("admin_activity") or data.get("is_admin"): reasons.append("abnormal admin activity"); techniques.append("T1098")
        if data.get("impossible_travel"): reasons.append("impossible travel"); techniques.append("T1078")
        if data.get("rare_command"): reasons.append("rare command"); techniques.append("T1059")
        if data.get("unusual_network"): reasons.append("unusual network behavior"); techniques.append("T1046")
        score = min(100, 30 + len(reasons) * 15) if reasons else 0
        return BehaviorFinding(event.public() if hasattr(event, "public") else event, score, "; ".join(reasons) or "no anomalous behavior", min(1, score / 100 + .3), techniques)
