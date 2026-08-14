class IntelligenceEnricher:
 def enrich(self,indicators,fusion=None,graph=None): return [{**x,"relationships":[{"type":"indicator_observed"}],"enriched":True} for x in indicators]
