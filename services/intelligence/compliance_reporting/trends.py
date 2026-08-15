from .models import TrendSummary, Provenance
class TrendReportBuilder:
    def build(self,tenant_id,framework_id,snapshots,gaps=None):
        if len(snapshots)<2: return TrendSummary(tenant_id,framework_id,provenance=[Provenance("compliance_monitoring","","insufficient historical snapshots")])
        values=[x.coverage for x in snapshots]; direction="improving" if values[-1]>values[0] else "deteriorating" if values[-1]<values[0] else "stable"
        return TrendSummary(tenant_id,framework_id,direction,coverage_trend=values,readiness_trend=values,provenance=[Provenance("compliance_monitoring","","historical snapshots supplied by monitoring")])
