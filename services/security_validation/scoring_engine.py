class ScoringEngine:
 def calculate(self,detection,investigation,prevention,automation,ai):
  values=[detection,investigation,prevention,automation,ai]; return round(sum(values)/len(values),2)
