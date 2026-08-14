class AssetRepository:
 def __init__(self): self.assets={}
 def create_asset(self,a): self.assets[a.asset_id]=a; return a
 def get_asset(self,i,tenant_id=None):
  a=self.assets.get(i); return a if a and (tenant_id is None or a.tenant_id==tenant_id) else None
 def list_assets(self,tenant_id=None): return [a for a in self.assets.values() if tenant_id is None or a.tenant_id==tenant_id]
 def update_asset(self,i,**changes): a=self.assets[i]; [setattr(a,k,v) for k,v in changes.items() if hasattr(a,k)]; return a
 def delete_asset(self,i): return self.assets.pop(i,None) is not None
