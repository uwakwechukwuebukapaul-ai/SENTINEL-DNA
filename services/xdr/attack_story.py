from .models import AttackStory
class AttackStoryGenerator:
 def generate(self,org,incident_id,signals,confidence):
  stages=[]
  for s in signals: stages.append(s.metadata.get("mitre_stage",s.signal_type))
  summary="; ".join(s.metadata.get("description",s.signal_type) for s in signals) or "Correlated security activity detected."
  return AttackStory(org,incident_id,summary,"Unauthorized access or compromise"," -> ".join(stages[-3:]) or "INITIAL_ACCESS",confidence)
