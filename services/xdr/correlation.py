class CorrelationEngine:
 def correlate(self,signals):
  groups={}
  for s in signals: groups.setdefault((s.entity,s.entity_type),[]).append(s)
  return list(groups.values())
