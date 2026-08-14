from datetime import datetime,timezone
from uuid import uuid4
class CustomerZeroDemoPipeline:
 def __init__(self): self.runs=[]
 def run(self,organization_id,scenario="credential_attack"):
  from lab.lab_content.simulation_runner import SimulationRunner
  events=SimulationRunner().run(organization_id,scenario)
  run={"id":str(uuid4()),"organization_id":organization_id,"scenario":scenario,"synthetic":True,"telemetry":events["events"],"detections":events["detections"],"investigation":{"status":"COMPLETED","mitre_mapping":[e["event_type"] for e in events["events"]]},"threat_intelligence":{"status":"ENRICHED","confidence":.82},"threat_graph":{"status":"ANALYZED","attack_paths":1,"blast_radius":len(events["events"])},"risk":{"score":90,"severity":"CRITICAL","explanation":"Synthetic activity reaches a critical asset."},"prevention":{"status":"RECOMMENDED","actions":["isolate endpoint","disable account","block indicator"],"requires_approval":True},"soc_decision":{"status":"ESCALATED","confidence":.88},"executive_report":{"security_posture":"Improvement demonstrated","summary":"End-to-end synthetic attack validation completed."},"created_at":datetime.now(timezone.utc).isoformat()}; self.runs.append(run); return run
 def scoped(self,org): return [x for x in self.runs if x["organization_id"]==org]
