from .reasoning_engine import ReasoningEngine
class ReasoningGraphService:
 def __init__(self): self.engine=ReasoningEngine()
 def analyze(self,evidence=None,attack_paths=None):
  nodes,edges=self.engine.build_reasoning_graph(evidence); hypotheses=self.engine.generate_hypotheses(evidence); priorities=self.engine.rank_evidence(evidence); return {"nodes":[n.to_dict() for n in nodes],"edges":[e.to_dict() for e in edges],"hypotheses":[h.to_dict() for h in hypotheses],"priority_evidence":[p.to_dict() for p in priorities],"recommended_steps":self.engine.recommend_next_steps(evidence,attack_paths),"reasoning":"The investigation prioritizes evidence by confidence and attack relevance."}
