from .models import IntelligenceRecord
class IntelligenceAdapter:
    subsystem="unknown"
    def normalize(self,tenant_id,items):
        return [IntelligenceRecord(tenant_id,self.subsystem,str(x.get("id",x.get("source_record_id",""))),x.get("entity_type",self.subsystem),x.get("severity","unknown"),x.get("confidence"),x.get("status","unknown"),x.get("timestamp",""),{"source_subsystem":self.subsystem,"source_record_id":str(x.get("id",x.get("source_record_id",""))),"adapter":self.__class__.__name__},x.get("requires_human_review",False),dict(x)) for x in items or []]
class InvestigationAdapter(IntelligenceAdapter): subsystem="investigation"
class ThreatAdapter(IntelligenceAdapter): subsystem="threat_intelligence"
class EvidenceAdapter(IntelligenceAdapter): subsystem="evidence"
class IncidentAdapter(IntelligenceAdapter): subsystem="incident_management"
class ExposureAdapter(IntelligenceAdapter): subsystem="exposure_management"
class PostureAdapter(IntelligenceAdapter): subsystem="security_posture"
class ComplianceAdapter(IntelligenceAdapter): subsystem="compliance"
class GovernanceAdapter(IntelligenceAdapter): subsystem="governance_decision"
class OperationsAdapter(IntelligenceAdapter): subsystem="operations"
class ExecutiveRiskAdapter(IntelligenceAdapter): subsystem="executive_risk"
class CommandCenterAdapter(IntelligenceAdapter): subsystem="command_center"
