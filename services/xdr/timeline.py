class AttackTimelineBuilder:
 def build(self,signals): return [s.public() for s in sorted(signals,key=lambda x:x.timestamp)]
