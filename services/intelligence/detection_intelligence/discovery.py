import hashlib
from .models import DetectionCandidate
class DetectionDiscoveryEngine:
 def discover(self,investigations=None,threat_intelligence=None,attack_paths=None,threat_actors=None,campaigns=None):
  text=str([investigations,threat_intelligence,attack_paths,threat_actors,campaigns]).lower(); out=[]
  if "phish" in text or "credential" in text: out.append(DetectionCandidate("DC-"+hashlib.sha256(text.encode()).hexdigest()[:12],"Credential Harvesting URL","Detect repeated credential harvesting URL patterns",["investigation"],["T1566.002"],.88))
  if "ransomware" in text or "malware" in text: out.append(DetectionCandidate("DC-"+hashlib.sha256((text+"malware").encode()).hexdigest()[:12],"Malware Execution Pattern","Detect suspicious malware execution sequences",["investigation"],["T1204"],.82))
  return out
