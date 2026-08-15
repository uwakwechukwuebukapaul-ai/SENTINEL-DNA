class InvestmentRecommendations:
    def generate(self,priorities):
        for x in priorities: x.rationale += " Human leadership review is required."; x.requires_human_review=True
        return priorities
