class LearningEngine:
 def __init__(self,graph): self.graph=graph; self.insights=[]
 def learn(self,org,data):
  item={"organization_id":org,"pattern":data.get("pattern",""),"recommendation":data.get("recommendation",""),"source":data.get("source","analyst")}; self.insights.append(item); return item
