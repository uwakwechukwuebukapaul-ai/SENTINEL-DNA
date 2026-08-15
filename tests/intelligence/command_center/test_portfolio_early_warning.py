from services.intelligence.command_center.portfolio_early_warning_service import PortfolioEarlyWarningService
class C:
    def derive(self,t): return {'command_center':{'governance_posture':'governance_blocked','uncertainty':('high_uncertainty',)},'signals':()}
def test_warning_is_governance_attention_not_prediction():
    x=PortfolioEarlyWarningService(C()).derive('a'); assert x['early_warning']['warning_state']=='high'; assert x['advisory_only']
