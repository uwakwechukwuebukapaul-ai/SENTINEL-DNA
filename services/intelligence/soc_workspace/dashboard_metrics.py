from __future__ import annotations
from collections import Counter

def calculate_risk_distribution(records): return dict(Counter(str((r.get("risk") or {}).get("severity", "unknown") if isinstance(r.get("risk"),dict) else r.get("risk", "unknown")).lower() for r in records))
def calculate_investigation_volume(records): return {"total": len(records), "completed": sum(str(r.get("status", "")).lower() == "completed" for r in records)}
def calculate_ai_confidence(records):
    values=[float(r.get("confidence")) for r in records if r.get("confidence") is not None]; return {"average_confidence": round(sum(values)/len(values),4) if values else 0.0, "completed_investigations": len(values)}
def calculate_threat_activity(records): return {"campaigns": sum(len(r.get("threat_intelligence_report", {}).get("matched_indicators", [])) for r in records if isinstance(r.get("threat_intelligence_report"),dict))}
def calculate_hunting_activity(records): return {"active_hunts": sum(1 for r in records if str(r.get("status", "")).lower() in {"open","active"})}
