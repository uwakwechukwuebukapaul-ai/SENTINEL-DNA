from .models import SecurityPosture
class PostureEngine:
 def calculate(self,org,signals=None):
  signals=signals or {}; score=round(sum(float(signals.get(x,70)) for x in ("detection","response","exposure","vulnerability","validation","prevention","ai","compliance"))/8,2); level="Optimized" if score>=90 else "Managed" if score>=75 else "Defined" if score>=60 else "Developing" if score>=40 else "Reactive"; return SecurityPosture(org,score,round(100-score,2),level,["Strong control coverage"] if score>=75 else [],["Prioritize highest-risk exposure"] if score<85 else [])
