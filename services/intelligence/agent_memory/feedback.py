class FeedbackTracker:
 def __init__(self): self.feedback=[]
 def record(self,item): self.feedback.append(item); return item
 def metrics(self,agent_id=None):
  xs=[x.rating for x in self.feedback if agent_id is None or x.agent_id==agent_id]; return {"count":len(xs),"average_rating":round(sum(xs)/len(xs),2) if xs else 0.0}
