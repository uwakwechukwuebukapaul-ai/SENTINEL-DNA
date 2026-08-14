from dataclasses import asdict,dataclass
@dataclass
class RiskAssessment:
 score:float; severity:str; factors:dict; confidence:float; explanation:str
 def public(self): return asdict(self)
class XDRRiskEngine:
 def calculate(self,signals):
  sev={"INFO":10,"LOW":25,"MEDIUM":50,"HIGH":75,"CRITICAL":95}; score=min(100,sum(sev.get(s.severity.upper(),25) for s in signals)/max(1,len(signals))+min(20,len(signals)*3)); level="CRITICAL" if score>=85 else "HIGH" if score>=65 else "MEDIUM" if score>=35 else "LOW"; return RiskAssessment(round(score,2),level,{"signal_count":len(signals),"sources":sorted({s.source for s in signals})},round(sum(s.confidence for s in signals)/max(1,len(signals)),2),"Risk combines signal severity, confidence, and attack progression.")
