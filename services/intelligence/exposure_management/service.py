from .prioritizer import ExposurePrioritizer
from .repository import ExposureRepository
from .scoring import ExposureScoringEngine

class ExposureManagementService:
    def __init__(self, tenant_id=None, repository=None): self.tenant_id=tenant_id; self.repository=repository or ExposureRepository(); self.scoring=ExposureScoringEngine(); self.prioritizer=ExposurePrioritizer()
    def analyze_exposure(self, asset_id, **factors): return self.repository.save(self.scoring.calculate(self.tenant_id, asset_id, **factors))
    def prioritize_risk(self): return self.prioritizer.prioritize(self.repository.list(self.tenant_id))
    def generate_recommendations(self): return self.prioritizer.recommendations(self.repository.list(self.tenant_id))
