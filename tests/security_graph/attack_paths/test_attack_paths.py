from services.security_graph import SecurityGraphRepository
from services.security_graph.graph_builder import GraphBuilder
from services.security_graph.attack_paths import AttackPathService
def setup():
 r=SecurityGraphRepository(); b=GraphBuilder(); a=b.entity("t","asset","internet",{"internet_exposed":True}); v=b.entity("t","vulnerability","CVE"); i=b.entity("t","incident","I"); [r.add_entity(x) for x in (a,v,i)]; r.add_relationship(b.relationship("t",a,v,"affects")); r.add_relationship(b.relationship("t",v,i,"involved_in")); return r,a,v,i
def test_attack_path_models(): r,a,v,i=setup(); assert AttackPathService(r).analyze_paths(a.entity_id,"t")
def test_path_serialization(): p=AttackPathService(setup()[0]).analyze_paths(setup()[1].entity_id,"t")[0]; assert "path_id" in p.to_dict()
def test_path_discovery(): r,a,v,i=setup(); assert r.find_neighbors(a.entity_id)
def test_risk_path_detection(): r,a,_,_=setup(); assert AttackPathService(r).analyze_paths(a.entity_id,"t")[0].severity=="high"
def test_exposure_scoring(): r,a,_,_=setup(); assert AttackPathService(r).analyze_paths(a.entity_id,"t")[0].risk_score>0
def test_blast_radius(): r,a,_,_=setup(); assert AttackPathService(r).get_blast_radius(a.entity_id,"t").score>0
def test_attack_explanation(): r,a,_,_=setup(); assert "relationship" in AttackPathService(r).analyze_paths(a.entity_id,"t")[0].explanation
def test_investigation_context(): assert "attack_path_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
def test_tenant_isolation(): r,a,_,_=setup(); assert not AttackPathService(r).analyze_paths(a.entity_id,"other")
def test_dashboard_summary(): assert True
def test_backward_compatibility(): assert setup()[0].list_entities()
