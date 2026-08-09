"""
Autonomous Learning Pipeline

Coordinates Sentinel DNA learning cycle.
"""


from .feedback_engine import FeedbackEngine
from .investigation_memory import InvestigationMemory
from .pattern_learning import PatternLearning
from .model_improvement import ModelImprovement



class LearningPipeline:


    def __init__(self):

        self.feedback =
            FeedbackEngine()

        self.memory =
            InvestigationMemory()

        self.patterns =
            PatternLearning()

        self.improvement =
            ModelImprovement()



    def process(
        self,
        investigation,
        evaluation
    ):


        feedback = (
            self.feedback.analyze(
                evaluation
            )
        )


        self.memory.store(
            investigation
        )


        self.improvement.apply(
            feedback
        )


        return {

            "feedback":
                feedback,

            "memory_items":
                self.memory.count(),

            "improvements":
                len(
                    self.improvement.history()
                )
        }