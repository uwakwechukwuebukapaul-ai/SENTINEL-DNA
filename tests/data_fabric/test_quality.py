from services.data_fabric.quality import DataQualityService
def test_quality_has_insufficient_state():
    r=DataQualityService().report('t'); assert r.completeness=='insufficient_data'; assert r.advisory_only
