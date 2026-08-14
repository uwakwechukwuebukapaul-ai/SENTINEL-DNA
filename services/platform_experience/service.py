class PlatformExperienceService:
 def __init__(self): self.settings={}
 def context(self,org,role): return {"organization_id":org,"role":role,"demo_mode":self.settings.get(org,{}).get("demo_mode",False),"navigation":[{"label":"Overview","path":"/workspace/enterprise"},{"label":"Investigations","path":"/workspace/cases"},{"label":"Copilot","path":"/workspace/security-copilot"},{"label":"Threat Posture","path":"/workspace/exposure"},{"label":"Operations","path":"/workspace/operations"}]}
 def enable_demo(self,org): self.settings.setdefault(org,{})["demo_mode"]=True; return self.context(org,"demo")
