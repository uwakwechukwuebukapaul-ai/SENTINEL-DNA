class SimulationRunner:
 SCENARIOS={"credential_attack":["suspicious_login","privilege_change"],"malware_execution":["suspicious_process","malicious_download"],"ransomware":["mass_file_encryption","lateral_movement"],"insider_threat":["unusual_data_access","bulk_download"],"cloud_compromise":["unusual_api_activity","privilege_escalation"]}
 def run(self,org,scenario):
  events=[{"synthetic":True,"organization_id":org,"event_type":x,"severity":"HIGH","source":"lab","raw_data":{}} for x in self.SCENARIOS.get(scenario,[])]
  return {"organization_id":org,"scenario":scenario,"status":"COMPLETED","synthetic":True,"events":events,"detections":len(events),"investigations":1,"ai_decisions":1,"validation_score":85}
