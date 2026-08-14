from .models import DetectionFeedback, DetectionMetrics

class DetectionPerformanceEngine:
    def calculate(self, feedback: list[DetectionFeedback], detection_id: str = "") -> DetectionMetrics:
        tp = sum(bool(item.true_positive) for item in feedback); fp = sum(bool(item.false_positive) for item in feedback); total = len(feedback)
        precision = tp / (tp + fp) if tp + fp else 0.0
        false_positive_rate = fp / total if total else 0.0
        effectiveness = max(0.0, min(1.0, precision * (1.0 - false_positive_rate)))
        return DetectionMetrics(detection_id, total, tp, fp, precision, false_positive_rate, effectiveness, min(1.0, total / 10.0))
