from services.intelligence.detection_learning import (
    AnalystVerdict, DetectionFeedback, DetectionLearningService,
    DetectionMetrics, DetectionOptimizationEngine,
    InMemoryDetectionFeedbackRepository,
)
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_feedback_storage():
    repository = InMemoryDetectionFeedbackRepository()
    feedback = DetectionFeedback("det-1", AnalystVerdict.TRUE_POSITIVE, tenant_id="tenant-a")
    repository.save(feedback)
    assert repository.list("det-1", "tenant-a") == [feedback]

def test_tenant_isolation():
    repository = InMemoryDetectionFeedbackRepository()
    repository.save(DetectionFeedback("det-1", AnalystVerdict.TRUE_POSITIVE, tenant_id="a"))
    repository.save(DetectionFeedback("det-1", AnalystVerdict.FALSE_POSITIVE, tenant_id="b"))
    assert len(repository.list("det-1", "a")) == 1

def test_detection_metrics():
    service = DetectionLearningService(tenant_id="a")
    service.record_feedback(DetectionFeedback("det-1", AnalystVerdict.TRUE_POSITIVE))
    service.record_feedback(DetectionFeedback("det-1", AnalystVerdict.FALSE_POSITIVE))
    metrics = service.learn("det-1").metrics
    assert metrics.precision == .5 and metrics.false_positive_rate == .5

def test_optimizer_is_advisory():
    metrics = DetectionMetrics("det-1", 10, 2, 8, .2, .8, .04, 1.0)
    recommendations = DetectionOptimizationEngine().recommend(metrics)
    assert recommendations and all(item.requires_human_approval for item in recommendations)

def test_learning_cycle_with_memory_and_backward_compatible_result():
    memory = []
    class Memory:
        def remember(self, value):
            memory.append(value)
            return "memory-1"
    service = DetectionLearningService(memories=(Memory(),))
    service.record_feedback(DetectionFeedback("det-1", AnalystVerdict.TRUE_POSITIVE))
    context = service.learn("det-1")
    assert context.metrics.total_feedback == 1
    assert len(memory) == 1 and memory[0]["metrics"] == context.to_dict()["metrics"]
    assert InvestigationResult().detection_learning_context is None
