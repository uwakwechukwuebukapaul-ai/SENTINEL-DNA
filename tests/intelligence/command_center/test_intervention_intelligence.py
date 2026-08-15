from services.intelligence.command_center.intervention_intelligence import InterventionIntelligence
from services.intelligence.command_center.intervention_intelligence_service import InterventionIntelligenceService
class C:
    def derive(self,t): return {'command_center':{'governance_posture':'governed','early_warning_level':'insufficient_history','history_status':'insufficient_history'}}
class W:
    def derive(self,t): return {'early_warning':{'warning_state':'insufficient_history','signals':()}}
def test_intervention_is_deterministic_and_advisory():
    s=InterventionIntelligenceService(C(),W()); assert s.derive('a')==s.derive('a'); assert s.derive('a')['advisory_only']; assert InterventionIntelligence.__dataclass_params__.frozen
