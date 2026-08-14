from datetime import datetime,timezone
from .models import NormalizedIndicator
class IntelligencePipeline:
 def __init__(self,collector,normalizer,enricher,repository): self.collector,self.normalizer,self.enricher,self.repository=collector,normalizer,enricher,repository
 def process(self,source,payload):
  raw=self.collector.collect(source,payload); normalized=[]
  for item in raw:
   x=self.normalizer.normalize(item,source.source_id); n=NormalizedIndicator(**x,first_seen=datetime.now(timezone.utc).isoformat(),last_seen=datetime.now(timezone.utc).isoformat()); normalized.append(self.repository.save_indicator(n))
  return self.enricher.enrich([x.to_dict() for x in normalized])
