from .models import OptimizationCandidate
from .detection import DetectionAnalyzer
from .investigation import InvestigationAnalyzer
from .evidence import EvidenceAnalyzer
from .workflow import WorkflowAnalyzer
from .prioritization import OptimizationPrioritizer
from .repository import OptimizationRepository
class SOCOptimizationService:
    def __init__(self,repository=None,audit=None): self.repository=repository or OptimizationRepository(); self.audit=audit; self.analyzers={"DETECTION":DetectionAnalyzer(),"INVESTIGATION":InvestigationAnalyzer(),"EVIDENCE":EvidenceAnalyzer(),"WORKFLOW":WorkflowAnalyzer(),"PLAYBOOK":WorkflowAnalyzer()}; self.prioritizer=OptimizationPrioritizer()
    def _audit(self,event,**data):
        if self.audit and hasattr(self.audit,"record"): self.audit.record(event,**data)
    def _analyze(self,tenant_id,domain,signals):
        result=[]
        for x in self.analyzers[domain].analyze(tenant_id,signals):
            score=self.prioritizer.score(x); result.append(OptimizationCandidate(tenant_id,domain,x.category,f"Review {x.category.lower()} optimization opportunity",f"Observed {x.frequency} supporting signal(s); review is advisory and source systems are unchanged.",self.prioritizer.priority(x),score,x.confidence,x.references if x.domain=="" else x.references,x.references if domain=="EVIDENCE" else [],[x.key] if domain=="DETECTION" else [],[x.key] if domain=="INVESTIGATION" else [],[x.key] if domain in {"WORKFLOW","PLAYBOOK"} else [],x.provenance,uncertainty=x.uncertainty or ("UNKNOWN" if x.confidence is None else "")))
            self.repository.save(result[-1])
        return result
    def analyze_detection(self,t,s): return self._analyze(t,"DETECTION",s)
    def analyze_investigation(self,t,s): return self._analyze(t,"INVESTIGATION",s)
    def analyze_evidence(self,t,s): return self._analyze(t,"EVIDENCE",s)
    def analyze_workflow(self,t,s): return self._analyze(t,"WORKFLOW",s)
    def analyze_playbook(self,t,s): return self._analyze(t,"PLAYBOOK",s)
    def correlate_signals(self,tenant_id,signals): return [x for x in signals if x.tenant_id==tenant_id]
    def prioritize_candidates(self,tenant_id): return sorted(self.repository.list(tenant_id),key=lambda x:(-x.score,x.domain,x.category))
    def get_historical_optimization(self,tenant_id): return self.repository.list(tenant_id)
    def get_candidates(self,tenant_id,domain=None,priority=None): return self.repository.list(tenant_id,domain,priority)
