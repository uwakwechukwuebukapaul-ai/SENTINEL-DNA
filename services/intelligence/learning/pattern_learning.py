"""
Threat Pattern Learning Engine
"""


class PatternLearning:


    def __init__(self):

        self.patterns = {}


    def learn(
        self,
        category,
        indicators
    ):


        if category not in self.patterns:

            self.patterns[category] = []


        self.patterns[category].extend(
            indicators
        )


        return {

            "category":
                category,

            "patterns_learned":
                len(
                    self.patterns[category]
                )
        }


    def get_patterns(
        self,
        category
    ):

        return self.patterns.get(
            category,
            []
        )