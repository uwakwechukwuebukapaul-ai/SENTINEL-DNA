class DetectionOptimizer:
 def recommend(self,metrics,feedback):
  out=[]
  if metrics["false_positive_rate"]>.3: out.append({"type":"tuning","recommendation":"Tune rule filters to reduce false positives"})
  if metrics["precision"]<.5: out.append({"type":"visibility","recommendation":"Improve supporting telemetry and evidence coverage"})
  for x in feedback:
   if x.severity_adjustment: out.append({"type":"rule_improvement","recommendation":"Review severity calibration","note":x.tuning_notes})
  return out
