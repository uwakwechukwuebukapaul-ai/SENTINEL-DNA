from .models import EvidencePriority
class EvidencePriorityEngine:
 def rank(self,evidence):
  scored=[]
  for i,x in enumerate(evidence or []):
   text=str(x).lower(); score=.9 if any(k in text for k in ("memory dump","malware","credential","powershell")) else .4; scored.append((score,EvidencePriority(str(x.get("id") or x.get("evidence_id") or i),0,score,"High probability of confirming an attack signal." if score>.8 else "Requires contextual validation.")))
  scored.sort(key=lambda z:-z[0]); return [EvidencePriority(p.evidence_id,i+1,p.score,p.reason) for i,(_,p) in enumerate(scored)]
