class ExposureEngine:
 def calculate(self,internet_exposure=False,suspicious_communication=False,threat_matches=0,investigation_history=0):
  score=min(100,int(internet_exposure)*35+int(suspicious_communication)*25+threat_matches*20+investigation_history*10); level="low" if score<=30 else "medium" if score<=70 else "high"; return {"exposure_score":score,"exposure_level":level,"indicators":[],"recommendations":["Review exposed asset telemetry"] if score>30 else []}
