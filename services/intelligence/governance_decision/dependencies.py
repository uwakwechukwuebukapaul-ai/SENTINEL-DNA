from .models import DecisionDependency
class DependencyAnalyzer:
    def analyze(self,signals):
        result=[]
        for left,right in zip(signals,signals[1:]): result.append(DecisionDependency(from_signal=left.category,to_signal=right.category,explanation="Source intelligence may influence the downstream governance review; no action is executed."))
        return result
