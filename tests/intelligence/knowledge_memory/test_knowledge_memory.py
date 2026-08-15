from services.intelligence.knowledge_memory import KnowledgeMemoryRepository, KnowledgeMemoryService
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_memory_storage():
    record=KnowledgeMemoryService("a").store("investigation", {"summary":"phishing credential"}); assert record.tenant_id == "a"

def test_similarity_retrieval_and_lessons():
    service=KnowledgeMemoryService("a"); service.store("incident", {"summary":"phishing credential"}); assert service.find_similar("phishing"); assert service.generate_lessons()

def test_tenant_isolation():
    repository=KnowledgeMemoryRepository(); KnowledgeMemoryService("a", repository).store("incident", {"summary":"private"}); assert KnowledgeMemoryService("b", repository).search("private") == []

def test_backward_compatibility():
    result=InvestigationResult(); assert result.knowledge_memory_context is None and "knowledge_memory_context" in result.to_dict()
