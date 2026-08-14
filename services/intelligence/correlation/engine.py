from .models import CorrelationAnalysisResult, SecuritySignal
from .rules import STARTER_RULES

class DeterministicCorrelationEngine:
    def __init__(self, rules=STARTER_RULES): self.rules=tuple(rules)
    def correlate(self, signals: list[SecuritySignal], tenant_id=None):
        types={signal.signal_type for signal in signals}; matched=[]; confidence=0.0
        for rule in self.rules:
            overlap=types.intersection(rule.signal_types)
            if len(overlap) >= (2 if len(rule.signal_types) > 1 else 1): matched.append(rule.rule_id); confidence=max(confidence, rule.threshold)
        if any(signal.signal_type in {"ioc_match", "privilege_change", "malware"} for signal in signals): confidence=max(confidence,.85)
        risk="high" if confidence >= .8 else "medium" if confidence >= .6 else "low" if signals else "unknown"
        return CorrelationAnalysisResult(tenant_id, matched, signals, min(confidence,1.0), risk, false_positive=not matched and bool(signals))
