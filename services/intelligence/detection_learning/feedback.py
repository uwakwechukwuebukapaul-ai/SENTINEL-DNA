from .models import DetectionFeedback
from .repository import DetectionFeedbackRepository

class DetectionFeedbackCollector:
    def __init__(self, repository: DetectionFeedbackRepository) -> None: self.repository = repository
    def record(self, feedback: DetectionFeedback) -> DetectionFeedback: return self.repository.save(feedback)
