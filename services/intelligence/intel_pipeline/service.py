from .repository import IntelligencePipelineRepository
from .collector import OfflineCollector
from .normalizer import IndicatorNormalizer
from .enrichment import IntelligenceEnricher
from .pipeline import IntelligencePipeline
from .models import IntelligenceSource
class IntelligencePipelineService:
 def __init__(self): self.repository=IntelligencePipelineRepository(); self.pipeline=IntelligencePipeline(OfflineCollector(),IndicatorNormalizer(),IntelligenceEnricher(),self.repository)
 def ingest(self,source_id,name,feed_type,payload): return self.pipeline.process(IntelligenceSource(source_id,name,feed_type),payload)
 def indicators(self): return self.repository.list_indicators()
