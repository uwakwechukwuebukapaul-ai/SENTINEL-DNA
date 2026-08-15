from uuid import uuid4
from .learning import LearningEngine
from .models import KnowledgeRecord
from .repository import KnowledgeMemoryRepository
from .similarity import SimilarityEngine

class KnowledgeMemoryService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or KnowledgeMemoryRepository(); self.similarity=SimilarityEngine(); self.learning=LearningEngine()
    def store(self, source, content, tags=None): return self.repository.save(KnowledgeRecord(str(uuid4()), self.tenant_id, source, content, list(tags or [])))
    def search(self, query): return [record for score,record in self.similarity.rank(query, self.repository.list(self.tenant_id)) if score > 0]
    def find_similar(self, query): return self.search(query)
    def generate_lessons(self): return self.learning.lessons(self.tenant_id, self.repository.list(self.tenant_id))
