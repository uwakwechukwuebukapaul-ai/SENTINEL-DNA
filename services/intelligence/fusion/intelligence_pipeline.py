"""
Intelligence Pipeline

High-level execution workflow
for threat intelligence analysis.
"""


class IntelligencePipeline:
    """
    Coordinates intelligence investigation flow.
    """


    def __init__(
        self,
        fusion_engine,
    ):

        self.fusion_engine = (
            fusion_engine
        )



    def investigate(
        self,
        indicator,
        indicator_type=None,
    ):

        result = (
            self.fusion_engine.fuse(
                indicator,
                indicator_type,
            )
        )


        return {
            "indicator":
                indicator,

            "analysis":
                result.to_dict()
        }