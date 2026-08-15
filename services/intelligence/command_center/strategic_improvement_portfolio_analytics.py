from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class StrategicImprovementPortfolioAnalytics:
    tenant_id:str; portfolio_id:str; posture:str="insufficient_history"; improvement_themes:tuple=(); priority_distribution:tuple=(); lifecycle_analytics:tuple=(); unresolved_areas:tuple=(); learning_opportunities:tuple=(); effectiveness_patterns:tuple=(); strategic_focus_areas:tuple=(); evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
