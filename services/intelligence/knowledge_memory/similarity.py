import re

class SimilarityEngine:
    @staticmethod
    def _tokens(record): return set(re.findall(r"[a-z0-9]+", str(record.content if hasattr(record,"content") else record).lower()))
    def rank(self, query, records):
        query_tokens=set(re.findall(r"[a-z0-9]+", str(query).lower())); return sorted(((len(query_tokens & self._tokens(record)) / max(1,len(query_tokens | self._tokens(record))), record) for record in records), key=lambda item: item[0], reverse=True)
