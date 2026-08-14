class BlastRadiusEngine:
 def calculate(self,org,asset_id,assets,relationships):
  ids={asset_id}; changed=True
  while changed:
   changed=False
   for x in relationships:
    if x.source_asset in ids or x.target_asset in ids:
     for value in (x.source_asset,x.target_asset):
      if value not in ids: ids.add(value); changed=True
  return {"asset_id":asset_id,"affected_assets":[a.public() for a in assets if a.id in ids],"count":len(ids)}
