import hashlib
from .models import Hypothesis
class HypothesisEngine:
 def generate(self,evidence):
  text=str(evidence).lower(); out=[]
  if "powershell" in text and ("malware" in text or "hash" in text): out.append(Hypothesis("H-"+hashlib.sha256(text.encode()).hexdigest()[:12],"Endpoint may be executing malicious payload through PowerShell.",["powershell","malware"],.88,["Validate process tree","Review endpoint timeline"]))
  elif evidence: out.append(Hypothesis("H-"+hashlib.sha256(text.encode()).hexdigest()[:12],"Observed evidence requires analyst validation.",[],.55,["Collect corroborating evidence"]))
  return out
