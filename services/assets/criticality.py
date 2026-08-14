class CriticalityEngine:
 def calculate(self,asset_type,environment="unknown",department="",tags=None):
  if environment.lower() in {"production","prod"} and asset_type in {"database","server","application"}: return "critical"
  if asset_type in {"database","server"} or department.lower() in {"finance","security"}: return "high"
  if environment.lower() in {"development","dev"}: return "medium"
  return "low"
