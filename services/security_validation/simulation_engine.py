class SimulationEngine:
 def generate(self,scenario):
  return [{"synthetic":True,"event_type":x,"severity":scenario.severity,"mitre_mapping":[x],"description":"Synthetic %s telemetry"%scenario.attack_type} for x in scenario.mitre_techniques]
