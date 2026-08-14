from __future__ import annotations
from collections import Counter

def executive_metrics(results: list[dict]) -> dict:
    durations = [float(item.get("duration_ms", 0)) for item in results]
    scores = [float((item.get("risk") or {}).get("score", 0)) for item in results]
    confidence = [float(item.get("confidence", 0)) for item in results]
    techniques = {technique for item in results for technique in item.get("mitre", [])}
    return {"investigations_completed": len(results), "average_investigation_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0, "risk_distribution": dict(Counter("high" if score >= 70 else "medium" if score >= 40 else "low" for score in scores)), "mitre_coverage": sorted(techniques), "ai_confidence_score": round(sum(confidence) / len(confidence), 3) if confidence else 0}
