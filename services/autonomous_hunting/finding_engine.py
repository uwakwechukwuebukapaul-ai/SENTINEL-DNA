class FindingEngine:
 def merge(self,findings): return list({(x.entity,x.description):x for x in findings}.values())
