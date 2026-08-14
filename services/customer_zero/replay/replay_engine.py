from .replay_models import ReplayEvent
class ReplayEngine:
    def generate(self, result):
        return [ReplayEvent("09:01", "attack", f"{result.get('scenario', 'Scenario')} started"), ReplayEvent("09:03", "detection", f"{len(result.get('detections', []))} detections generated"), ReplayEvent("09:04", "investigation", "Investigation started"), ReplayEvent("09:05", "mitre", "MITRE techniques mapped"), ReplayEvent("09:06", "response", "Response actions generated")]
