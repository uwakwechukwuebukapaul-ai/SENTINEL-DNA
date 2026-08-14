class DetectionCoverage:
 def analyze(self,covered,required):
  missing=sorted(set(required)-set(covered)); score=round(len(set(covered)&set(required))/max(1,len(set(required)))*100,2); return {"mitre_coverage":score,"visibility_gaps":missing,"detection_maturity":"advanced" if score>=80 else "developing" if score>=40 else "initial"}
