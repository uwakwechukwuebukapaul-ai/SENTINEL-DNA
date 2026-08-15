from dataclasses import asdict,dataclass
@dataclass(frozen=True)
class GovernanceLearningCommandCenter:
    tenant_id:str; command_center_id:str; learning_posture:str="insufficient_history"; effectiveness_summary:str="insufficient_history"; outcome_summary:str="unknown"; recurring_themes:tuple=(); improvement_signals:tuple=(); learning_opportunities:tuple=(); evidence_strength:str|None=None; confidence:str|float|None=None; uncertainty:tuple=(); provenance:tuple=(); recommendations:tuple=(); advisory_only:bool=True
    def to_dict(self): return asdict(self)
