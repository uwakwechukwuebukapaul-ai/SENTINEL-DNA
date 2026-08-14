class IntelligencePipelineRepository:
 def __init__(self): self.indicators={}; self.sources={}
 def save_source(self,x): self.sources[x.source_id]=x; return x
 def save_indicator(self,x): self.indicators[x.indicator_id]=x; return x
 def list_indicators(self): return list(self.indicators.values())
