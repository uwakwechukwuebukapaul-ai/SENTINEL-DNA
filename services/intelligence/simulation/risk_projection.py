class RiskProjectionEngine:
 def project(self,twin,phases):
  current=min(100,len(phases)*15+len(twin.vulnerabilities)*10+len(twin.attack_paths)*10); improvement=len(twin.controls)*8; return current,max(0,current-improvement),improvement
