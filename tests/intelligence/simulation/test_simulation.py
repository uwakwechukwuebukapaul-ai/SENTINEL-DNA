from services.intelligence.simulation import SimulationService
def twin(): return SimulationService().builder.build(assets=[{"id":"a"}],identities=[{"id":"i"}],vulnerabilities=[{"id":"v"}],controls=[],attack_paths=[{"id":"p"}])
def test_attack_simulation(): assert "initial_access" in SimulationService().simulator.simulate(twin())
def test_digital_twin(): assert twin().to_dict()["assets"]
def test_scenario_analysis(): assert SimulationService().create_scenario("MFA",{"mfa_enabled":True}).changes["mfa_enabled"]
def test_risk_projection(): assert SimulationService().simulate(twin(),SimulationService().create_scenario("patch",{"vulnerability_patched":True})).projected_risk>=0
def test_control_impact():
 s=SimulationService(); r=s.simulate(twin(),s.create_scenario("detect",{"detection_added":True})); assert r.control_impact>0
def test_backward_compatibility(): assert "simulation_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
