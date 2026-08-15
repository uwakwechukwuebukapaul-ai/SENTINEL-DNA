from services.intelligence.command_center.escalation_lifecycle_service import EscalationLifecycleService
class E:
    def derive(self,t): return {'escalations':()}
def test_lifecycle_does_not_fabricate_history(): assert EscalationLifecycleService(E()).derive('a')['lifecycle']['lifecycle_state']=='insufficient_history'
