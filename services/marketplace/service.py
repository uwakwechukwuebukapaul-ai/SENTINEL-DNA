from uuid import uuid4
class MarketplaceService:
    TYPES = {"sigma_rule_package", "detection_pack", "playbook", "intelligence_package"}
    def __init__(self): self.packages = {}
    def publish(self, organization_id, name, package_type, content):
        if package_type not in self.TYPES: raise ValueError("invalid_package_type")
        item = {"id": str(uuid4()), "organization_id": organization_id, "name": name, "package_type": package_type, "content": content, "status": "draft"}; self.packages[item["id"]] = item; return item
    def list(self, organization_id): return [x for x in self.packages.values() if x["organization_id"] == organization_id]
