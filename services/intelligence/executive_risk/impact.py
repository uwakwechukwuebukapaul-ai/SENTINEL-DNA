class BusinessImpactEngine:
    def estimate(self,asset): return round((asset.revenue_impact+asset.operational_impact+asset.regulatory_impact)/3,2)
