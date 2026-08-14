class BaseSOCAgent:
 def initialize(self,context): return {"initialized":True}
 def analyze(self,context): return {"status":"analyzed","agent":self.agent_id}
 def validate(self,result): return True
 def summarize(self,result): return result
