class PreventionValidator:
 def score(self,recommendation=None,approval=False): return 100.0 if recommendation and approval else 60.0 if recommendation else 0.0
