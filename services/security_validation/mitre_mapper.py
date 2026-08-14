class MITREMapper:
 def map(self,scenario): return [{"technique":x,"coverage":"PENDING"} for x in scenario.mitre_techniques]
