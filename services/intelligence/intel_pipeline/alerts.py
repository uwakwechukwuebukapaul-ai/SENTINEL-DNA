class IntelligenceAlertEngine:
 def generate(self,indicators,cases=None): return [{"type":"investigation_correlation","indicator":x.value,"cases":list(cases or [])} for x in indicators if cases]
