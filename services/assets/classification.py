class AssetClassifier:
 def normalize_asset_type(self,value): return str(value or "unknown").lower().replace(" ","_")
 def classify_asset(self,hostname,metadata=None):
  h=str(hostname).lower(); m=str(metadata or {}).lower()
  if "db" in h or "database" in m:return "database"
  if "app" in h:return "application"
  if "srv" in h or "server" in m:return "server"
  if "cloud" in m:return "cloud_resource"
  return "workstation"
