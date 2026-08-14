from .models import SecurityRecommendation
class AdvisorRecommendationEngine:
 def generate(self,org,score): return [SecurityRecommendation(org,"P1","Prioritize controls with the highest exposure reduction",20,"Medium")] if score<85 else []
