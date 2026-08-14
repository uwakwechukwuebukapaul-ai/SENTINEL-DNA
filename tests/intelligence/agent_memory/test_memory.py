from services.intelligence.agent_memory import AgentMemoryService,AgentExperience,AgentMessage,CollaborationContext
def test_experience_serialization(): assert AgentExperience("e","t","a","c","x").to_dict()["experience_id"]=="e"
def test_memory_storage(): assert AgentMemoryService().remember_experience("t","a","c","x",{},.8).confidence==.8
def test_tenant_isolation():
 s=AgentMemoryService(); s.remember_experience("t","a","c","x",{},.8); assert s.confidence_metrics("other")["count"]==0
def test_message_bus():
 s=AgentMemoryService(); s.publish("t","a","b","finding",{"x":1}); assert len(s.bus.receive("b","t"))==1
def test_collaboration_context(): assert CollaborationContext("c","t").case_id=="c"
def test_feedback_metrics():
 s=AgentMemoryService(); s.feedback.record(type("F",(),{"agent_id":"a","rating":5})()); assert s.feedback.metrics("a")["average_rating"]==5
def test_confidence_metrics():
 s=AgentMemoryService(); s.remember_experience("t","a","c","x",{},.8); assert s.confidence_metrics("t")["average_confidence"]==.8
def test_investigation_integration(): assert "agent_memory_context" in __import__('services.intelligence.investigation.investigation_result',fromlist=['InvestigationResult']).InvestigationResult().to_dict()
def test_deterministic_behavior():
 s=AgentMemoryService(); a=s.remember_experience("t","a","c","x",{}); b=s.remember_experience("t","a","c","x",{}); assert a.experience_id==b.experience_id
