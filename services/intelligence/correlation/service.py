from uuid import uuid4
from .engine import DeterministicCorrelationEngine
from .models import InvestigationTrigger, SecuritySignal
from .repository import CorrelationRepository

class CorrelationService:
    def __init__(self, tenant_id=None, repository=None, engine=None): self.tenant_id=tenant_id; self.repository=repository or CorrelationRepository(); self.engine=engine or DeterministicCorrelationEngine()
    def correlate(self, signals):
        valid=[signal for signal in signals if signal.tenant_id == self.tenant_id]
        for signal in valid: self.repository.save_signal(signal)
        return self.engine.correlate(valid, self.tenant_id)
    def evaluate(self, result, confidence_threshold=.75): return result.confidence >= confidence_threshold and result.risk in {"medium", "high"} and not result.false_positive
    def create_trigger(self, result, confidence_threshold=.75):
        if not self.evaluate(result, confidence_threshold): return None
        return self.repository.save_trigger(InvestigationTrigger(str(uuid4()), self.tenant_id, ", ".join(result.matched_rules), result.confidence, result.risk, tuple(signal.signal_id for signal in result.signals)))
