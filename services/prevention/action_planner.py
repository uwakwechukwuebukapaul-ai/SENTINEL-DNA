from .models import SecurityAction
class ActionPlanner:
 def plan(self,org,target,reason,risk_score):
  types=["ISOLATE_ENDPOINT","BLOCK_IP","DISABLE_ACCOUNT"] if risk_score>=85 else ["BLOCK_IP","CREATE_FIREWALL_RULE"]
  return [SecurityAction(org,x,target,reason,True) for x in types]
