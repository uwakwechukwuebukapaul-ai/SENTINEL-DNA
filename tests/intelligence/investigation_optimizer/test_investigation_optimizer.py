from services.intelligence.investigation_optimizer import InvestigationOptimizationRepository, InvestigationOptimizationService
from services.intelligence.investigation.investigation_result import InvestigationResult

def test_plan_optimization():
    result=InvestigationOptimizationService("a").optimize_plan("p1", ["assess_risk", "collect_evidence", "reason_over_graph"]); assert result.recommendations[0].step == "collect_evidence" and result.advisory_only

def test_step_recommendation(): assert InvestigationOptimizationService("a").recommend_steps(["document_findings", "collect_evidence"])[0].step == "collect_evidence"

def test_tenant_isolation():
    repository=InvestigationOptimizationRepository(); InvestigationOptimizationService("a", repository).optimize_plan("p", ["collect_evidence"]); assert InvestigationOptimizationService("b", repository).repository.list("b") == []

def test_historical_comparison(): assert InvestigationOptimizationService("a").compare_investigations([{"steps":[1,2]}])["average_steps"] == 2

def test_backward_compatibility():
    result=InvestigationResult(); assert result.investigation_optimization_context is None and "investigation_optimization_context" in result.to_dict()
