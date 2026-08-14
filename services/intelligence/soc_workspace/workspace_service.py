from __future__ import annotations
from datetime import datetime, timezone
from .models import SOCWorkspaceSnapshot, CaseWorkspaceView, ThreatPostureSummary
from .dashboard_metrics import calculate_risk_distribution, calculate_investigation_volume, calculate_ai_confidence, calculate_threat_activity, calculate_hunting_activity

class SOCWorkspaceService:
    """Read-only aggregation boundary; component failures yield partial views."""
    def __init__(self, cases=None, case_repository=None, **components):
        self.cases = cases if cases is not None else case_repository
        self.components = components
    def _records(self):
        source=self.cases
        if source is None: return []
        if isinstance(source,dict): return list(source.values())
        if hasattr(source,"list_all"): return list(source.list_all())
        return list(source)
    @staticmethod
    def _dict(x):
        if x is None:return None
        return x.to_dict() if hasattr(x,"to_dict") else x
    def get_investigation_metrics(self):
        rows=self._records(); return {"volume":calculate_investigation_volume(rows),"risk_distribution":calculate_risk_distribution(rows),"ai":calculate_ai_confidence(rows)}
    def get_workspace_snapshot(self):
        rows=self._records(); risk=calculate_risk_distribution(rows); ai=calculate_ai_confidence(rows); ti=calculate_threat_activity(rows); hunts=calculate_hunting_activity(rows)
        return SOCWorkspaceSnapshot(datetime.now(timezone.utc).isoformat(),len(rows),risk.get("high",0),risk.get("critical",0),ti.get("campaigns",0),hunts.get("active_hunts",0),ai["average_confidence"],self.get_investigation_metrics(),True)
    def get_case_workspace(self, case_id):
        row=next((r for r in self._records() if str(r.get("case_id"))==str(case_id)),None)
        if row is None:return None
        def part(key):
            try:return self._dict(row.get(key))
            except Exception:return None
        risk=row.get("risk",{}); severity=risk.get("severity","unknown") if isinstance(risk,dict) else risk
        return CaseWorkspaceView(str(case_id),str(severity),str(row.get("status","unknown")),part("evidence"),part("threat_intelligence_report"),part("hunting_summary"),part("reasoning_report"),part("decision_report"),part("copilot_summary"),part("narrative_report"))
    def get_threat_posture(self):
        rows=self._records(); scores=[float(r.get("threat_intelligence_report",{}).get("threat_score",0)) for r in rows if isinstance(r.get("threat_intelligence_report"),dict)]; indicators=[]; techniques=[]
        for r in rows:
            report=r.get("threat_intelligence_report",{}) or {}; indicators += [str(x.get("indicator",{}).get("value")) for x in report.get("matched_indicators",[]) if isinstance(x,dict)]; techniques += list(r.get("mitre",[]) or [])
        return ThreatPostureSummary(len(rows),round(sum(scores)/len(scores),2) if scores else 0.0,sorted(set(indicators)),[],sorted(set(techniques)),calculate_risk_distribution(rows))
