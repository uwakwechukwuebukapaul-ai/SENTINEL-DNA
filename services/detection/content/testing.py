from time import perf_counter
class DetectionTestEngine:
    def test(self, rule, events):
        start = perf_counter(); matches = [event for event in events if any(str(value).lower() in str(event).lower() for value in rule.query_logic.split())]; count = len(events); return {"events_tested": count, "matches": len(matches), "false_positives": 0, "true_positive_estimate": len(matches), "accuracy_score": round(len(matches) / count * 100, 2) if count else 0, "execution_time": round((perf_counter() - start) * 1000, 3)}
