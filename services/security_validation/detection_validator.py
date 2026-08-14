class DetectionValidator:
 def score(self,events,detected=None): return round(100*len(detected or [])/max(1,len(events)),2)
