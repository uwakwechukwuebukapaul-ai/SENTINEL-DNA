from .models import SecurityPostureScore

class PostureBenchmark:
    def compare(self, current: SecurityPostureScore, baseline=None):
        if baseline is None: return {"overall_delta": 0.0, "domain_deltas": {}, "benchmark": "no_baseline"}
        previous={item.domain:item.score for item in baseline.domain_scores}; return {"overall_delta": round(current.overall_score-baseline.overall_score,2), "domain_deltas": {item.domain: round(item.score-previous.get(item.domain,0),2) for item in current.domain_scores}, "benchmark": "baseline"}
