class ExecutiveRiskAggregator:
    def summarize(self,assets,findings): return {"asset_count":len(assets),"finding_count":len(findings),"critical_assets":sum(x.criticality=="critical" for x in assets),"high_findings":sum(x.severity in {"high","critical"} for x in findings)}
