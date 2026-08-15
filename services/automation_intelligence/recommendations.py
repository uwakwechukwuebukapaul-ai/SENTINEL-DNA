class RecommendationEngine:
    def filter_advisory(self, recommendations):
        for recommendation in recommendations: recommendation.requires_human_review=True
        return recommendations
