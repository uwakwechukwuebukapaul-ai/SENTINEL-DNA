from datetime import datetime,timezone
class FreshnessEngine:
 def confidence(self,indicator,now=None):
  age=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(indicator.last_seen.replace("Z","+00:00"))).days) if indicator.last_seen else 0; return round(indicator.confidence*(.95**age),4)
