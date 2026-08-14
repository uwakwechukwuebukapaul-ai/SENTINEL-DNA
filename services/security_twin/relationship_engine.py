class RelationshipEngine:
 def neighbors(self,repository,org,asset_id): return [x for x in repository.scoped(repository.relationships,org) if x.source_asset==asset_id or x.target_asset==asset_id]
