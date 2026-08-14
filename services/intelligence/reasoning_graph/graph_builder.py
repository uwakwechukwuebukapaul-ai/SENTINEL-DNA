from .models import ReasoningNode,ReasoningEdge
class ReasoningGraphBuilder:
 def build(self,evidence=None,signals=None):
  nodes=[ReasoningNode(str(x.get("id") or x.get("evidence_id") or i),"evidence",str(x.get("id") or i),.7,"Observed investigation evidence") for i,x in enumerate(evidence or []) if isinstance(x,dict)]; return nodes,[]
