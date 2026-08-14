class MaturityEngine:
 def level(self,scores): return "Optimized" if sum(scores)/max(1,len(scores))>=90 else "Managed" if sum(scores)/max(1,len(scores))>=75 else "Defined"
