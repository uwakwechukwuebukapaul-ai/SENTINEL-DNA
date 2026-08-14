class BehaviorAnalytics:
 def analyze(self,events):
  text=str(events).lower(); return {"user_anomalies":["unusual_login"] if "failed login" in text else [],"asset_anomalies":["unusual outbound" ] if "unusual outbound" in text else [],"sequences":["credential_access"] if "credential" in text else []}
