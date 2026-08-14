class ExecutiveReportEngine:
 def generate(self,posture,risks,recommendations): return {"security_posture":posture.public(),"risks":[x.public() for x in risks],"recommendations":[x.public() for x in recommendations],"summary":"Executive security posture and risk reduction report."}
