class ScenarioEngine:
 def apply(self,twin,scenario):
  changes=scenario.changes
  if changes.get("mfa_enabled"): twin.identities=[{**x,"mfa":True} for x in twin.identities]
  if changes.get("vulnerability_patched"): twin.vulnerabilities=[]
  if changes.get("detection_added"): twin.controls=twin.controls+[ {"type":"detection"} ]
  return twin
