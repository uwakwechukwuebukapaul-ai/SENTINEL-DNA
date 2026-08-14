class ApprovalManager:
 SENSITIVE={"response","soar_execution","external_integration","containment"}
 def required(self,action): return action in self.SENSITIVE
 def approve(self,action,approved=False): return approved if self.required(action) else True
