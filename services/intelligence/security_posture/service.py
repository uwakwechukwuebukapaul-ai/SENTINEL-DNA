from .benchmark import PostureBenchmark
from .models import PostureRecommendation
from .repository import SecurityPostureRepository
from .scoring import SecurityPostureScoringEngine

class SecurityPostureService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or SecurityPostureRepository(); self.scoring=SecurityPostureScoringEngine(); self.benchmark=PostureBenchmark()
    def calculate_posture(self, signals=None): return self.repository.save(self.scoring.calculate(self.tenant_id, signals))
    def generate_recommendations(self):
        posture=self.repository.get(self.tenant_id); return [PostureRecommendation(item.domain, f"Improve {item.domain.replace('_',' ')}", f"Current domain score is {item.score}", "high" if item.score < 50 else "medium") for item in (posture.domain_scores if posture else []) if item.score < 70]
    def compare_posture(self, baseline=None):
        posture=self.repository.get(self.tenant_id); return self.benchmark.compare(posture, baseline) if posture else {"benchmark": "no_current_posture"}
