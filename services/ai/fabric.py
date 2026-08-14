from .providers import LocalLLMProvider
from .security import PromptSecurity
from .rag import RAGRetriever
class ReasoningFabric:
    def __init__(self, provider=None, retriever=None): self.provider = provider or LocalLLMProvider(); self.retriever = retriever or RAGRetriever(); self.security = PromptSecurity()
    def investigate(self, organization_id, question, evidence=None):
        self.security.validate(question); context = self.security.isolate(organization_id, self.retriever.retrieve(organization_id, question)); safe_evidence = self.security.filter_sensitive(evidence or [])
        return {"answer": self.provider.analyze(self.security.filter_sensitive(question), context), "evidence": safe_evidence, "reasoning": [f"Retrieved {len(context)} tenant-scoped context items"], "confidence": 0.5 if not context else 0.75, "recommendation": "Review supporting evidence and confirm the next response action."}
