from services.intelligence.command_center.strategic_planning_service import StrategicPlanningService
class Strategy:
    def derive(self,tenant): return {"tenant_id":tenant,"posture":{"posture":"watch","confidence":"medium"},"strategic_signals":[{"tenant_id":tenant,"signal_id":"s1","signal_type":"regression","title":"Detection regression","organizational_dimension":"detection","priority":"high","evidence_strength":"strong","confidence":"medium","uncertainty":[],"provenance":{"source":"strategy"},"contributing_references":["r1"]}]}
def test_planning_is_deterministic_tenant_scoped_and_advisory():
    s=StrategicPlanningService(Strategy()); a=s.derive("a"); assert a==s.derive("a"); assert a["planning"]["planning_status"]=="actionable"; assert a["advisory_only"] is True; assert a["priorities"][0]["classification"]=="unresolved_priority"; assert s.derive("b")["tenant_id"]=="b"
def test_no_history_is_explicit():
    empty=type("S",(),{"derive":lambda self,t:{"tenant_id":t,"posture":{},"strategic_signals":[]}})(); a=StrategicPlanningService(empty).derive("a"); assert a["planning"]["planning_status"]=="insufficient_history"; assert a["history"]==[]
def test_missing_signal_is_safe(): assert StrategicPlanningService(Strategy()).detail("a","missing") is None
