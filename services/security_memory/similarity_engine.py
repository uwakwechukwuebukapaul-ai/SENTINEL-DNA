class SimilarityEngine:
 def find(self,entities,term): return [x for x in entities if term.lower() in (x.name+" "+x.description).lower()]
