from .models import Asset
from .repository import AssetRepository

class AssetService:
    def __init__(self, repository=None): self.repository = repository or AssetRepository()
    def create(self, organization_id, data):
        return self.repository.save(Asset(organization_id=organization_id, hostname=str(data.get("hostname", "")).strip(), ip_address=data.get("ip_address", ""), asset_type=data.get("asset_type", "SERVER"), owner=data.get("owner", ""), criticality=data.get("criticality", "MEDIUM"), environment=data.get("environment", "production"), tags=data.get("tags", [])))
    def list(self, organization_id): return self.repository.list(organization_id)
    def get(self, organization_id, item_id): return self.repository.get(organization_id, item_id)
