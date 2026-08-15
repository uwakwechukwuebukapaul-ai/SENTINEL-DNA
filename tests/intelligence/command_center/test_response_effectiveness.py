from services.intelligence.command_center.response_effectiveness_service import ResponseEffectivenessService
def test_effectiveness_does_not_claim_causality():
    x=ResponseEffectivenessService().derive('a'); assert x['effectiveness']['evidence_sufficiency']=='insufficient_evidence'; assert 'insufficient evidence' in x['effectiveness']['effectiveness_assessment']
