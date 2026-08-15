class ControlAnalyzer:
    def evaluate(self,control): return control.status.lower() in {"implemented","compliant","effective","passed"}
