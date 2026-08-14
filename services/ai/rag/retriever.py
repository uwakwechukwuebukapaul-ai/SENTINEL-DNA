class RAGRetriever:
    def __init__(self, memory=None, threat_intelligence=None, mitre=None, cases=None): self.sources = [x for x in (memory, threat_intelligence, mitre, cases) if x]
    def retrieve(self, organization_id, query, limit=10):
        terms = set(str(query).lower().split()); found = []
        for source in self.sources:
            records = source.search(organization_id, limit=limit) if hasattr(source, "search") else source
            for record in records or []:
                if not terms or terms.intersection(str(record).lower().split()): found.append(record)
        return found[:limit]
