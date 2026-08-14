class PriorityEngine:
 def calculate(self,data):
  score=0; score+={"LOW":10,"MEDIUM":30,"HIGH":60,"CRITICAL":85}.get(str(data.get("severity","MEDIUM")).upper(),30); score+=min(10,int(data.get("blast_radius",0))); score+=min(10,int(data.get("business_impact",0))); return "P1" if score>=85 else "P2" if score>=60 else "P3" if score>=30 else "P4"
