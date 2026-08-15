from services.intelligence.command_center.decision_readiness_service import DecisionReadinessService
class P:
    def derive(self,t): return {'policy_review':{'policy_readiness':'insufficient_history'},'governance':{}}
class O:
    def derive(self,t): return {'decision_oversight':{'decision_history_status':'insufficient_decision_history'}}
def test_readiness_preserves_insufficient_history():
    x=DecisionReadinessService(P(),O()).derive('a'); assert x['readiness']['readiness_classification']=='insufficient_history'; assert x['advisory_only']
