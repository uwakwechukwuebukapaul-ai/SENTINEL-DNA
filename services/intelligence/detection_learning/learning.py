class LearningCycle:
 def __init__(self,performance,optimizer): self.performance,self.optimizer=performance,optimizer
 def run(self,feedback):
  metrics=self.performance.calculate(feedback); return {"metrics":metrics,"recommendations":self.optimizer.recommend(metrics,feedback),"automatic_changes":False}
