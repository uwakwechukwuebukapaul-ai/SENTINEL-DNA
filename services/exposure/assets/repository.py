class AssetRepository:
    def __init__(self): self._items = {}
    def save(self, item): self._items[item.id] = item; return item
    def get(self, organization_id, item_id):
        item = self._items.get(item_id); return item if item and item.organization_id == organization_id else None
    def list(self, organization_id): return [x for x in self._items.values() if x.organization_id == organization_id]
