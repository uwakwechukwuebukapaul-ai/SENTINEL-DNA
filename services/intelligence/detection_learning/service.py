from .feedback import DetectionFeedbackCollector
from .learning import LearningMemory
from .models import DetectionFeedback, LearningContext
from .optimizer import DetectionOptimizationEngine
from .performance import DetectionPerformanceEngine
from .repository import DetectionFeedbackRepository, InMemoryDetectionFeedbackRepository

class DetectionLearningService:
    def __init__(self, repository: DetectionFeedbackRepository | None = None, memories=(), audit_logger=None, tenant_id: str | None = None) -> None:
        self.repository = repository or InMemoryDetectionFeedbackRepository(); self.collector = DetectionFeedbackCollector(self.repository); self.performance = DetectionPerformanceEngine(); self.optimizer = DetectionOptimizationEngine(); self.memory = LearningMemory(*memories); self.audit_logger = audit_logger; self.tenant_id = tenant_id
    def record_feedback(self, feedback: DetectionFeedback | None = None, **kwargs) -> DetectionFeedback:
        if feedback is None:
            feedback = DetectionFeedback(**kwargs)
        if self.tenant_id is not None and feedback.tenant_id not in (None, self.tenant_id): raise ValueError("feedback tenant does not match service tenant")
        if self.tenant_id is not None and feedback.tenant_id is None:
            from dataclasses import replace
            feedback = replace(feedback, tenant_id=self.tenant_id)
        result = self.collector.record(feedback)
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record("detection_feedback_recorded", detection_id=result.detection_id, tenant_id=result.tenant_id)
        return result
    def analyze(self, tenant_id: str | None = None) -> dict:
        rows = self.repository.list(tenant_id=tenant_id)
        detection_id = rows[0].detection_id if rows else ""
        context = self.learn(detection_id) if detection_id else LearningContext()
        return {"metrics": context.metrics.__dict__ if context.metrics else {}, "recommendations": [item.__dict__ for item in context.recommendations], "automatic_changes": False, "learning_context": context.to_dict()}
    def learn(self, detection_id: str) -> LearningContext:
        metrics = self.performance.calculate(self.repository.list(detection_id, self.tenant_id), detection_id); context = LearningContext(metrics, tuple(self.optimizer.recommend(metrics))); refs = self.memory.remember(context); result = LearningContext(metrics, context.recommendations, refs)
        if self.audit_logger and hasattr(self.audit_logger, "record"): self.audit_logger.record("detection_learning_recommendations_generated", detection_id=detection_id, tenant_id=self.tenant_id, recommendation_count=len(result.recommendations), requires_human_approval=True)
        return result
