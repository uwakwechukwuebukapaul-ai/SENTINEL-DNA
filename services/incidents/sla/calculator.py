from datetime import datetime, timezone
class SLACalculator:
    def calculate(self, timestamps):
        def delta(a, b):
            if not timestamps.get(a) or not timestamps.get(b): return None
            return round((datetime.fromisoformat(timestamps[b]) - datetime.fromisoformat(timestamps[a])).total_seconds(), 2)
        return {"MTTA": delta("NEW", "TRIAGED"), "MTTD": delta("NEW", "INVESTIGATING"), "MTTI": delta("TRIAGED", "INVESTIGATING"), "MTTR": delta("NEW", "RESOLVED")}
