from .repository import DetectionLearningRepository
from .feedback import FeedbackService
from .performance import DetectionPerformanceEngine
from .optimizer import DetectionOptimizer
from .learning import LearningCycle
class DetectionLearningService:
 def __init__(self,repository=None): self.repository=repository or DetectionLearningRepository(); self.feedback=FeedbackService(); self.cycle=LearningCycle(DetectionPerformanceEngine(),DetectionOptimizer())
 def record_feedback(self,**kwargs): return self.repository.save_feedback(self.feedback.create(**kwargs))
 def analyze(self,tenant_id="default",detection_id=None): return self.cycle.run(self.repository.list_feedback(tenant_id,detection_id))
