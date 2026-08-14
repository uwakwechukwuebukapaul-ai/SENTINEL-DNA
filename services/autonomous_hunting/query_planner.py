class QueryPlanner:
 def build(self,hypothesis): return 'FROM events WHERE technique="%s" WITHIN 24h' % (hypothesis.mitre_techniques[0] if hypothesis.mitre_techniques else "unknown")
