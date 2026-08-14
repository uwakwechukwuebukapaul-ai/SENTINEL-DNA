class PolicyEngine:
 def requires_approval(self,action_type,target,criticality="MEDIUM"): return criticality.upper() in ("HIGH","CRITICAL") or action_type in ("DISABLE_ACCOUNT","ISOLATE_ENDPOINT","CREATE_FIREWALL_RULE")
