class IOCFusionEngine:
 def correlate(self,iocs,cases=None,assets=None,investigations=None,graph=None):
  known=set(iocs or []); return {"matched_iocs":sorted(known),"cases":list(cases or []),"assets":list(assets or []),"investigations":list(investigations or []),"graph_relationships":[{"source":x,"target":"case","relationship":"associated_with"} for x in sorted(known)]}
