class BusinessAssetCatalog:
    def __init__(self,repository): self.repository=repository
    def register(self,asset): return self.repository.save_asset(asset)
    def list(self,tenant_id): return self.repository.list_assets(tenant_id)
