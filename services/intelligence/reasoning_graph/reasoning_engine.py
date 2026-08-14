from .graph_builder import ReasoningGraphBuilder
from .hypothesis import HypothesisEngine
from .evidence_priority import EvidencePriorityEngine
from .planner import ReasoningInvestigationPlanner
class ReasoningEngine:
 def __init__(self): self.builder=ReasoningGraphBuilder(); self.hypotheses=HypothesisEngine(); self.priority=EvidencePriorityEngine(); self.planner=ReasoningInvestigationPlanner()
 def build_reasoning_graph(self,evidence=None,signals=None): return self.builder.build(evidence,signals)
 def generate_hypotheses(self,evidence): return self.hypotheses.generate(evidence)
 def rank_evidence(self,evidence): return self.priority.rank(evidence)
 def recommend_next_steps(self,evidence,attack_paths=None): return self.planner.plan(self.generate_hypotheses(evidence),self.rank_evidence(evidence),attack_paths)
