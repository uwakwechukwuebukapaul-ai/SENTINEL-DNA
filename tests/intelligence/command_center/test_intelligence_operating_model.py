from services.intelligence.command_center.intelligence_operating_model_service import IntelligenceOperatingModelService
def test_operating_model_insufficient_history_and_stable_id():
    a=IntelligenceOperatingModelService(None,None).derive('t')['operating_model']; b=IntelligenceOperatingModelService(None,None).derive('t')['operating_model']; assert a['model_id']==b['model_id']; assert a['operating_model_maturity']=='insufficient_history'; assert a['advisory_only']
