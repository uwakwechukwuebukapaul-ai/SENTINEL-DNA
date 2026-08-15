class InvestmentAggregator:
    def summarize(self,opportunities,priorities): return {"opportunity_count":len(opportunities),"priority_count":len(priorities),"categories":sorted({x.category for x in opportunities}),"top_opportunity":priorities[0].opportunity_id if priorities else None}
