class InvestmentScenarioEngine:
    def compare(self,opportunities,current_risk): return [{"opportunity_id":x.opportunity_id,"risk_after":round(current_risk*(1-max(x.current_control_effectiveness,.8)),2)} for x in opportunities]
