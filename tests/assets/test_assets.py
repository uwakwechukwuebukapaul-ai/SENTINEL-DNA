from services.assets import AssetService
def test_asset_models(): assert AssetService().register_asset(asset_id="a",tenant_id="t",hostname="db-prod-01").asset_id=="a"
def test_asset_serialization(): assert "hostname" in AssetService().register_asset(asset_id="a",tenant_id="t",hostname="x").to_dict()
def test_asset_repository():
 s=AssetService(); s.register_asset(asset_id="a",tenant_id="t",hostname="x"); assert s.repository.get_asset("a","t")
def test_tenant_isolation():
 s=AssetService(); s.register_asset(asset_id="a",tenant_id="t",hostname="x"); assert s.repository.get_asset("a","other") is None
def test_asset_classification(): assert AssetService().register_asset(asset_id="a",tenant_id="t",hostname="db-prod-01").asset_type=="database"
def test_criticality_scoring(): assert AssetService().register_asset(asset_id="a",tenant_id="t",hostname="db-prod-01",environment="production").criticality=="critical"
def test_exposure_scoring(): assert AssetService().exposure.calculate(internet_exposure=True)["exposure_score"]==35
def test_risk_integration(): assert AssetService().get_asset_profile("a") is None
def test_investigation_context(): assert "asset_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
def test_dashboard_summary(): assert AssetService().get_attack_surface_summary()["total_assets"]==0
def test_backward_compatibility(): assert AssetService().list_critical_assets()==[]
