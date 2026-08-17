"""
Sentinel DNA Application Container.

Builds and manages the enterprise
service dependency graph.

The container owns construction of shared
application services and guarantees that
dependent services receive the same
runtime instances.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.core.service_registry import (
    ServiceRegistry,
)

from services.intelligence.cases.case_manager import (
    CaseManager,
)

from services.intelligence.orchestration.investigation_orchestrator import (
    InvestigationOrchestrator,
)

from services.intelligence.orchestration.investigation_coordinator import (
    InvestigationCoordinator,
)
from services.intelligence.ai_runtime import AIRuntimeService

from services.intelligence.agents.agent_registry import (
    AgentRegistry,
)

from services.intelligence.agents.bootstrap import (
    bootstrap_agents,
)

from services.intelligence.agents.runtime_adapter import (
    AgentRuntimeAdapter,
)

from services.intelligence.runtime.runtime_task_executor import (
    RuntimeTaskExecutor,
)

from services.intelligence.dashboard.dashboard_service import (
    DashboardService,
)
from services.auth.auth_service import AuthService
from services.cases.case_service import CaseService
from services.audit.service import AuditService
from services.intelligence.investigation_optimizer import FeedbackRecommendationService, InvestigationOptimizationService
from services.tenancy.service import TenancyService
from services.connectors.registry import ConnectorRegistry
from services.governance.service import GovernanceService
from services.forensics.service import ForensicsService
from services.marketplace.service import MarketplaceService
from services.incidents.service import IncidentService
from services.api_management.service import APIManagementService
from services.billing.service import BillingService
from services.mssp.service import MSSPService
from services.compliance.service import ComplianceService
from services.mlops.service import MLOpsService
from services.monitoring.service import MonitoringService
from services.customer_success.service import CustomerSuccessService
from services.product_analytics.service import ProductAnalyticsService
from services.pilot_analytics.service import PilotAnalyticsService
from services.pilot_reports.service import PilotReportService
from services.pilot_management.service import PilotManagementService
from services.support.service import SupportService
from services.exercises.service import ExerciseService
from services.case_studies.service import CaseStudyService
from services.readiness.readiness_service import ReadinessService
from services.incidents.workflow.service import WorkflowService
from services.incidents.collaboration.service import CollaborationService
from services.incidents.sla.calculator import SLACalculator
from services.detection.content.service import DetectionContentService
from services.intelligence.threat.service import ThreatIntelligenceService
from services.intelligence.feeds.service import ThreatFeedService
from services.exposure.assets.service import AssetService
from services.exposure.vulnerability.service import VulnerabilityService
from services.exposure.scoring.engine import ExposureRiskEngine
from services.exposure.attack_path.analyzer import AttackPathAnalyzer
from services.data_lake.repository import SecurityEventRepository
from services.data_lake.query_engine import SecurityQueryEngine
from services.data_lake.retention import RetentionService
from services.data_lake.analytics import AnalyticsService
from services.analytics.ueba.repository import UebaRepository
from services.analytics.ueba.profiler import BehaviorProfiler
from services.analytics.ueba.anomaly_engine import AnomalyDetectionEngine
from services.analytics.ueba.risk_engine import EntityRiskEngine
from services.detection.discovery.analyzer import DetectionDiscoveryEngine
from services.intelligence.agents.agent_registry import AgentRegistry
from services.ai_agents.memory import AgentMemoryStore
from services.ai_agents.supervisor import AgentSupervisor
from services.graph.repository import GraphRepository
from services.graph.analyzer import ThreatGraphAnalyzer
from services.query_engine.executor import SecurityQueryExecutor
from services.xdr.repository import XDRRepository
from services.xdr.fusion_engine import XDRFusionEngine
from services.autonomous_hunting.repository import HuntingRepository
from services.autonomous_hunting.hypothesis_engine import HypothesisEngine
from services.autonomous_hunting.detection_generator import DetectionGenerator
from services.security_twin.repository import SecurityTwinRepository
from services.security_twin.integration import SecurityTwinService
from services.prevention.repository import PreventionRepository
from services.prevention.prevention_engine import PreventionEngine
from services.prevention.approval_manager import ApprovalManager
from services.prevention.control_executor import ControlExecutor
from services.prevention.outcome_tracker import OutcomeTracker
from services.security_validation.repository import ValidationRepository
from services.security_validation.attack_library import SCENARIOS
from services.security_validation.models import ValidationScenario,ValidationExecution,ValidationResult
from services.security_validation.simulation_engine import SimulationEngine
from services.security_validation.scoring_engine import ScoringEngine
from services.security_memory.graph import KnowledgeGraphEngine
from services.security_memory.relationship_manager import RelationshipManager
from services.security_memory.learning_engine import LearningEngine
from services.soc_manager.repository import SOCRepository
from services.soc_manager.task_manager import TaskManager
from services.soc_manager.supervisor import SOCSupervisor
from services.soc_manager.performance_engine import PerformanceEngine
from services.security_advisor.repository import AdvisorRepository
from services.security_advisor.risk_engine import PostureEngine
from services.security_advisor.forecast_engine import RiskForecastEngine
from services.security_advisor.recommendation_engine import AdvisorRecommendationEngine
from services.security_advisor.executive_report import ExecutiveReportEngine
from services.marketplace.repository import MarketplaceRepository
from services.marketplace.validator import PackageValidator
from services.marketplace.publisher import PackagePublisher
from services.marketplace.installer import PackageInstaller
from services.marketplace.rating_engine import RatingEngine
from lab.lab_content.manager import LabManager
from lab.lab_content.simulation_runner import SimulationRunner
from services.customer_zero.demo_pipeline import CustomerZeroDemoPipeline
from services.operations_hardening.service import OperationsHardeningService
from services.pilot_simulation.service import PilotSimulationService
from services.compliance.governance import GovernanceService
from services.identity_security.service import IdentitySecurityService
from services.identity.canonical_authority import CanonicalAuthorityService
from services.identity.request_context import CanonicalRequestContextService
from services.tenant.authorization import CanonicalTenantAuthorizationService
from database.connection import database
from services.billing.repository import BillingRepository
from services.billing.application import BillingApplicationService
from services.billing.readiness import BillingRouteReadinessEvaluator
from services.billing.capabilities import CanonicalAuthorizationAdapter
from services.billing.config import BillingConfiguration, EnvironmentSecretProvider
from services.billing.paystack import PaystackPaymentProvider, PaystackProviderValidator
from services.billing.config import CryptoConfiguration
from services.data_security.service import DataSecurityService
from services.decision_intelligence.service import DecisionIntelligenceService
from services.security_copilot.service import SecurityCopilotService
from services.platform_experience.service import PlatformExperienceService
from app.intelligence.gateway import ThreatIntelligenceGateway
from services.intelligence.fusion import ProviderNeutralFusionEngine
class SecurityValidationService:
    def __init__(self,repo): self.repo=repo
    def scenario(self,org,data):
        x=ValidationScenario(org,data.get("name","Scenario"),data.get("description","Synthetic validation"),data.get("attack_type","credential_theft"),data.get("mitre_techniques",SCENARIOS.get(data.get("attack_type","credential_theft"),[]))); self.repo.scenarios.append(x); return x
    def run(self,org,scenario_id):
        s=next(x for x in self.repo.scenarios if x.id==scenario_id and x.organization_id==org); e=ValidationExecution(org,s.id,"COMPLETED"); self.repo.executions.append(e); events=SimulationEngine().generate(s); score=ScoringEngine().calculate(100,80,60,70,80); r=ValidationResult(org,e.id,100,80,60,70,80,score,["Prevention validation requires approved action"],["Review prevention policy and approval coverage"]); self.repo.results.append(r); e.score=score; return r.public()


def build_feedback_recommendation_service(tenant_id: str) -> FeedbackRecommendationService:
    """Build the tenant-scoped canonical feedback recommendation seam."""
    return FeedbackRecommendationService(InvestigationOptimizationService(tenant_id))


def build_container() -> ServiceRegistry:
    """
    Build and return the Sentinel DNA service container.

    Dependency graph:

        CaseManager

        AgentRegistry
             |
             v
        RuntimeTaskExecutor
             |
             v
        InvestigationCoordinator
             |
             v
        InvestigationOrchestrator

        DashboardService

    All shared application services are instantiated
    once and registered in the service registry.
    """

    registry = ServiceRegistry()

    # ==================================
    # Core Intelligence Services
    # ==================================

    case_manager = CaseManager()

    # The canonical authority is the sole tenant/actor authorization source
    # for provider lookups.  No providers are enabled by default, preserving
    # the offline, zero-network runtime until an explicit provider adapter is
    # approved and injected here.
    canonical_authority = CanonicalAuthorityService()
    canonical_request_context = CanonicalRequestContextService(canonical_authority)
    canonical_authorization = CanonicalTenantAuthorizationService(canonical_authority)

    def authorize_threat_intelligence(tenant_id: str, actor_id: str) -> bool:
        return canonical_authorization.can_access_tenant(
            SimpleNamespace(tenant_id=tenant_id, actor_id=actor_id),
            tenant_id,
        )

    threat_intelligence_gateway = ThreatIntelligenceGateway(
        providers=(),
        authorize=authorize_threat_intelligence,
    )
    provider_neutral_fusion_engine = ProviderNeutralFusionEngine()

    agent_registry = AgentRegistry()

    runtime_executor = RuntimeTaskExecutor()

    runtime_adapter = AgentRuntimeAdapter(
        runtime_executor,
    )

    bootstrap_agents(
        agent_registry,
        runtime_adapter=runtime_adapter,
    )

    orchestrator = InvestigationOrchestrator(
        case_manager=case_manager,
        ai_runtime=AIRuntimeService.from_environment(),
    )

    coordinator = InvestigationCoordinator(
        registry=agent_registry,
        runtime=runtime_executor,
        orchestrator=orchestrator,
        threat_intelligence_gateway=threat_intelligence_gateway,
        provider_neutral_fusion_engine=provider_neutral_fusion_engine,
    )

    dashboard_service = DashboardService()
    audit_service = AuditService()
    auth_service = AuthService()
    case_service = CaseService()
    tenancy_service = TenancyService()
    connector_registry = ConnectorRegistry()
    governance_service = GovernanceService(); forensics_service = ForensicsService(); marketplace_service = MarketplaceService()
    incident_service = IncidentService(); api_management_service = APIManagementService()
    billing_service = BillingService()
    billing_repository = BillingRepository(database)
    billing_application = BillingApplicationService(billing_service, billing_repository)
    billing_readiness = BillingRouteReadinessEvaluator()
    billing_configuration = BillingConfiguration.from_environment()
    billing_secret_provider = EnvironmentSecretProvider()
    crypto_configuration = CryptoConfiguration.from_environment()
    paystack_provider = None
    paystack_validator = None
    if billing_configuration.reason_codes() == ("PAYSTACK_READY",):
        try:
            paystack_provider = PaystackPaymentProvider(
                base_url=billing_configuration.base_url,
                secret_provider=billing_secret_provider,
                secret_reference=billing_configuration.secret_key_reference,
                callback_url=billing_configuration.callback_url,
                timeout_seconds=billing_configuration.timeout_seconds,
            )
            paystack_validator = PaystackProviderValidator(paystack_provider)
        except Exception:
            paystack_provider = None
    mssp_service = MSSPService(); compliance_service = ComplianceService(); mlops_service = MLOpsService()
    monitoring_service = MonitoringService()
    customer_success_service = CustomerSuccessService()
    product_analytics_service = ProductAnalyticsService()
    pilot_analytics_service = PilotAnalyticsService(); pilot_report_service = PilotReportService()
    pilot_management_service = PilotManagementService(); support_service = SupportService()
    exercise_service = ExerciseService(); case_study_service = CaseStudyService()
    readiness_service = ReadinessService(service_lookup=lambda name: registry.get(name) if registry.has(name) else None)
    workflow_service = WorkflowService(); collaboration_service = CollaborationService(); sla_calculator = SLACalculator()
    detection_content_service = DetectionContentService()
    threat_service = ThreatIntelligenceService(); threat_feed_service = ThreatFeedService()
    asset_service = AssetService(); vulnerability_service = VulnerabilityService(); exposure_risk_engine = ExposureRiskEngine(); attack_path_analyzer = AttackPathAnalyzer()
    data_event_repository = SecurityEventRepository(); security_query_engine = SecurityQueryEngine(data_event_repository); retention_service = RetentionService(); analytics_service = AnalyticsService(data_event_repository)
    ueba_repository = UebaRepository(); behavior_profiler = BehaviorProfiler(ueba_repository); anomaly_detection_engine = AnomalyDetectionEngine(ueba_repository); entity_risk_engine = EntityRiskEngine(); detection_discovery_engine = DetectionDiscoveryEngine()
    agent_registry = AgentRegistry(); agent_memory = AgentMemoryStore(); agent_supervisor = AgentSupervisor(agent_registry, agent_memory); graph_repository = GraphRepository(); graph_analyzer = ThreatGraphAnalyzer(graph_repository); security_query_executor = SecurityQueryExecutor(security_query_engine)
    xdr_repository = XDRRepository(); xdr_engine = XDRFusionEngine(xdr_repository)
    autonomous_hunting_repository = HuntingRepository(); autonomous_hypothesis_engine = HypothesisEngine(autonomous_hunting_repository); autonomous_detection_generator = DetectionGenerator()
    security_twin_repository = SecurityTwinRepository(); security_twin_service = SecurityTwinService(security_twin_repository)
    prevention_repository = PreventionRepository(); prevention_engine = PreventionEngine(prevention_repository); approval_manager = ApprovalManager(); control_executor = ControlExecutor(); outcome_tracker = OutcomeTracker(prevention_repository)
    security_validation_repository = ValidationRepository(); security_validation_service = SecurityValidationService(security_validation_repository)
    knowledge_graph = KnowledgeGraphEngine(); memory_relationship_manager = RelationshipManager(knowledge_graph); memory_learning_engine = LearningEngine(knowledge_graph)
    soc_repository = SOCRepository(); soc_task_manager = TaskManager(soc_repository); soc_supervisor = SOCSupervisor(soc_repository); soc_performance_engine = PerformanceEngine()
    advisor_repository = AdvisorRepository(); posture_engine = PostureEngine(); risk_forecast_engine = RiskForecastEngine(); advisor_recommendation_engine = AdvisorRecommendationEngine(); advisor_report_engine = ExecutiveReportEngine()
    marketplace_repository = MarketplaceRepository(); marketplace_validator = PackageValidator(); marketplace_publisher = PackagePublisher(marketplace_repository,marketplace_validator); marketplace_installer = PackageInstaller(marketplace_repository); marketplace_rating_engine = RatingEngine()
    lab_manager = LabManager(); simulation_runner = SimulationRunner()
    customer_zero_demo_pipeline = CustomerZeroDemoPipeline()
    operations_hardening = OperationsHardeningService()
    pilot_simulation = PilotSimulationService()
    governance_compliance = GovernanceService()
    identity_security = IdentitySecurityService()
    data_security = DataSecurityService()
    decision_intelligence = DecisionIntelligenceService()
    security_copilot = SecurityCopilotService()
    platform_experience = PlatformExperienceService()
    billing_authorization = CanonicalAuthorizationAdapter(canonical_authorization)
    for component in ("database","redis","workers","audit","tenant_isolation","ai_governance"): operations_hardening.check(component)

    # ==================================
    # Register Services
    # ==================================

    registry.register(
        "case_manager",
        case_manager,
    )

    registry.register(
        "agent_registry",
        agent_registry,
    )

    registry.register(
        "runtime_task_executor",
        runtime_executor,
    )

    registry.register(
        "investigation_coordinator",
        coordinator,
    )

    registry.register("threat_intelligence_gateway", threat_intelligence_gateway)
    registry.register("provider_neutral_fusion_engine", provider_neutral_fusion_engine)

    # Legacy container key retained for dashboard integrations.
    registry.register("coordinator", coordinator)

    registry.register(
        "investigation_orchestrator",
        orchestrator,
    )

    registry.register(
        "dashboard_service",
        dashboard_service,
    )
    registry.register("audit_service", audit_service)
    registry.register("feedback_recommendation_service_factory", build_feedback_recommendation_service)
    registry.register("auth_service", auth_service)
    registry.register("case_service", case_service)
    registry.register("tenancy_service", tenancy_service)
    registry.register("connector_registry", connector_registry)
    registry.register("governance_service", governance_service)
    registry.register("forensics_service", forensics_service)
    registry.register("marketplace_service", marketplace_service)
    registry.register("incident_service", incident_service)
    registry.register("api_management_service", api_management_service)
    registry.register("billing_service", billing_service)
    registry.register("billing_repository", billing_repository)
    registry.register("billing_application", billing_application)
    registry.register("billing_readiness", billing_readiness)
    registry.register("billing_configuration", billing_configuration)
    registry.register("billing_secret_provider", billing_secret_provider)
    registry.register("paystack_provider", paystack_provider)
    registry.register("paystack_provider_validator", paystack_validator)
    registry.register("crypto_configuration", crypto_configuration)
    registry.register("crypto_provider", None)
    registry.register("billing_authorization", billing_authorization)
    registry.register("billing_context_provider", None)
    registry.register("mssp_service", mssp_service)
    registry.register("compliance_service", compliance_service)
    registry.register("mlops_service", mlops_service)
    registry.register("monitoring_service", monitoring_service)
    registry.register("customer_success_service", customer_success_service)
    registry.register("product_analytics_service", product_analytics_service)
    registry.register("pilot_analytics_service", pilot_analytics_service); registry.register("pilot_report_service", pilot_report_service)
    registry.register("pilot_management_service", pilot_management_service); registry.register("support_service", support_service)
    registry.register("exercise_service", exercise_service); registry.register("case_study_service", case_study_service)
    registry.register("readiness_service", readiness_service)
    registry.register("workflow_service", workflow_service); registry.register("collaboration_service", collaboration_service); registry.register("sla_calculator", sla_calculator)
    registry.register("detection_content_service", detection_content_service)
    registry.register("threat_service", threat_service); registry.register("threat_feed_service", threat_feed_service)
    registry.register("asset_service", asset_service); registry.register("vulnerability_service", vulnerability_service)
    registry.register("exposure_risk_engine", exposure_risk_engine); registry.register("attack_path_analyzer", attack_path_analyzer)
    registry.register("data_event_repository", data_event_repository); registry.register("security_query_engine", security_query_engine)
    registry.register("retention_service", retention_service); registry.register("analytics_service", analytics_service)
    registry.register("ueba_repository", ueba_repository); registry.register("behavior_profiler", behavior_profiler); registry.register("anomaly_detection_engine", anomaly_detection_engine); registry.register("entity_risk_engine", entity_risk_engine); registry.register("detection_discovery_engine", detection_discovery_engine)
    registry.register("agent_registry", agent_registry); registry.register("agent_memory", agent_memory); registry.register("agent_supervisor", agent_supervisor); registry.register("graph_repository", graph_repository); registry.register("graph_analyzer", graph_analyzer); registry.register("security_query_executor", security_query_executor)
    registry.register("xdr_repository", xdr_repository); registry.register("xdr_engine", xdr_engine)
    registry.register("autonomous_hunting_repository", autonomous_hunting_repository); registry.register("autonomous_hypothesis_engine", autonomous_hypothesis_engine); registry.register("autonomous_detection_generator", autonomous_detection_generator)
    registry.register("security_twin_repository", security_twin_repository); registry.register("security_twin_service", security_twin_service)
    registry.register("prevention_repository", prevention_repository); registry.register("prevention_engine", prevention_engine); registry.register("approval_manager", approval_manager); registry.register("control_executor", control_executor); registry.register("outcome_tracker", outcome_tracker)
    registry.register("security_validation_repository", security_validation_repository); registry.register("security_validation_service", security_validation_service)
    registry.register("knowledge_graph", knowledge_graph); registry.register("memory_relationship_manager", memory_relationship_manager); registry.register("memory_learning_engine", memory_learning_engine)
    registry.register("soc_repository", soc_repository); registry.register("soc_task_manager", soc_task_manager); registry.register("soc_supervisor", soc_supervisor); registry.register("soc_performance_engine", soc_performance_engine)
    registry.register("advisor_repository", advisor_repository); registry.register("posture_engine", posture_engine); registry.register("risk_forecast_engine", risk_forecast_engine); registry.register("advisor_recommendation_engine", advisor_recommendation_engine); registry.register("advisor_report_engine", advisor_report_engine)
    registry.register("marketplace_repository", marketplace_repository); registry.register("marketplace_publisher", marketplace_publisher); registry.register("marketplace_installer", marketplace_installer); registry.register("marketplace_rating_engine", marketplace_rating_engine)
    registry.register("lab_manager", lab_manager); registry.register("simulation_runner", simulation_runner)
    registry.register("customer_zero_demo_pipeline", customer_zero_demo_pipeline)
    registry.register("operations_hardening", operations_hardening)
    registry.register("pilot_simulation", pilot_simulation)
    registry.register("governance_compliance", governance_compliance)
    registry.register("identity_security", identity_security)
    registry.register("data_security", data_security)
    registry.register("decision_intelligence", decision_intelligence)
    registry.register("security_copilot", security_copilot)
    registry.register("platform_experience", platform_experience)
    registry.register("canonical_authority", canonical_authority)
    registry.register("canonical_request_context", canonical_request_context)
    registry.register("canonical_authorization", canonical_authorization)

    registry.validate_required((
        "investigation_coordinator",
        "investigation_orchestrator",
        "runtime_task_executor",
        "audit_service",
        "auth_service",
        "tenancy_service",
    ))
    return registry
