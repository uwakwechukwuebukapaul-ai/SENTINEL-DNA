from services.security_graph import GraphEntity,GraphRelationship,SecurityGraphRepository,GraphEnrichmentService
from services.security_graph.graph_builder import GraphBuilder
def setup():
 r=SecurityGraphRepository(); b=GraphBuilder(); a=b.entity("t","asset","db"); c=b.entity("t","campaign","camp"); r.add_entity(a); r.add_entity(c); r.add_relationship(b.relationship("t",a,c,"associated_with")); return r,a,c
def test_entity_models(): assert setup()[1].entity_type=="asset"
def test_relationship_models(): assert setup()[0].get_relationships()[0].relationship_type=="associated_with"
def test_serialization(): assert "entity_id" in setup()[1].to_dict()
def test_repository(): assert setup()[0].get_entity(setup()[1].entity_id,"t")
def test_duplicate_prevention(): r,a,c=setup(); r.add_relationship(GraphBuilder().relationship("t",a,c,"associated_with")); assert len(r.get_relationships())==1
def test_relationship_creation(): assert setup()[0].find_neighbors(setup()[1].entity_id)
def test_graph_builder(): assert GraphBuilder().entity("t","IOC","x").name=="x"
def test_query_engine(): r,a,c=setup(); assert r.find_neighbors(a.entity_id)
def test_attack_path_detection(): r,a,c=setup(); assert len(__import__('services.security_graph.query_engine',fromlist=['GraphQueryEngine']).GraphQueryEngine(r).get_attack_path(a.entity_id,c.entity_id,"t"))==2
def test_investigation_enrichment(): r,a,c=setup(); assert "related_campaigns" in GraphEnrichmentService(r).enrich_investigation(a.entity_id,"t")
def test_tenant_isolation(): r,a,c=setup(); assert r.get_entity(a.entity_id,"other") is None
def test_dashboard_summary(): assert GraphEnrichmentService(setup()[0]).posture("t")["total_entities"]==2
def test_backward_compatibility(): assert setup()[0].list_entities()
