def adapt_asset_risk(asset,exposure):
 score=min(100,(30 if asset.criticality=="critical" else 20 if asset.criticality=="high" else 10)+exposure.get("exposure_score",0)); return {"asset_id":asset.asset_id,"risk_score":score,"business_impact":asset.criticality,"exposure_level":exposure.get("exposure_level","low")}
