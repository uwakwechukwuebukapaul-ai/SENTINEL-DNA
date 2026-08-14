from .models import DetectionMetrics, Recommendation

class DetectionOptimizationEngine:
    """Produces advisory recommendations; it never mutates detection rules."""
    def recommend(self, metrics: DetectionMetrics) -> list[Recommendation]:
        recommendations = []
        if metrics.false_positive_rate >= .25:
            recommendations.append(Recommendation(metrics.detection_id, "rule_improvement", "False positives are high", "high", ("tighten predicates", "add exclusion conditions")))
        if metrics.confidence < .5:
            recommendations.append(Recommendation(metrics.detection_id, "visibility_improvement", "Insufficient analyst feedback", "medium", ("collect more verdicts", "instrument analyst outcomes")))
        if metrics.precision < .6 and metrics.total_feedback:
            recommendations.append(Recommendation(metrics.detection_id, "tuning", "Precision is below target", "high", ("review threshold", "recalibrate severity")))
        return recommendations
