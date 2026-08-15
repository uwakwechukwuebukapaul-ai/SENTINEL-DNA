class DependencyAnalyzer:
    def analyze(self,dependencies): return [x for x in dependencies if x.get("status") not in {None,"healthy","ok"}]
