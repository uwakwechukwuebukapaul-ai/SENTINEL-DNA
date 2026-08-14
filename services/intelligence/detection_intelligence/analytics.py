from .behavior import BehaviorAnalytics
class DetectionAnalytics:
 def __init__(self): self.behavior=BehaviorAnalytics()
 def analyze(self,events): return self.behavior.analyze(events)
