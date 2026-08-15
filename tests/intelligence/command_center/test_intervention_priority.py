from services.intelligence.command_center.intervention_priority_service import InterventionPriorityService
class I:
    def derive(self,t): return {'intervention':{'intervention_priority':'P1_ELEVATED_REVIEW','confidence':'medium'}}
def test_priority_is_review_attention_not_escalation_command():
    x=InterventionPriorityService(I()).derive('a'); assert x['priority']['priority']=='P1_ELEVATED_REVIEW'; assert x['advisory_only']
