class DetectionPerformanceEngine:
 def calculate(self,feedback):
  tp=sum(x.true_positive for x in feedback); fp=sum(x.false_positive for x in feedback); total=tp+fp; precision=tp/total if total else 0.; fpr=fp/total if total else 0.; effectiveness=round(precision*(1-fpr),4); return {"precision":round(precision,4),"false_positive_rate":round(fpr,4),"effectiveness_score":effectiveness,"confidence":round(min(1,total/10),4)}
