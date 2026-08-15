from services.intelligence.command_center.strategic_risk_coordination_service import StrategicRiskCoordinationService
class C:
    def derive(self,t): return {'command_center':{'governance_posture':'insufficient_history','strategic_risks':('risk',)}}
def test_coordination_preserves_insufficient_history():
    x=StrategicRiskCoordinationService(C()).derive('a'); assert x['coordination']['posture']=='insufficient_history'; assert x['advisory_only']
