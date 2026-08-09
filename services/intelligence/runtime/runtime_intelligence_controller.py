"""
Runtime Intelligence Controller

Runtime API facade.
"""


class RuntimeIntelligenceController:


    def __init__(
        self,
        intelligence_service,
    ):

        self.service = intelligence_service



    def execute(
        self,
        signals,
        case_id=None,
    ):

        result = (
            self.service.investigate(
                signals,
                case_id,
            )
        )

        return result.to_dict()