"""
Sentinel DNA Attack Chain Builder
"""


class AttackChain:



    def __init__(self):

        self.techniques = []



    def add(
        self,
        technique,
    ):

        self.techniques.append(
            technique
        )



    def build(self):

        return [

            item.to_dict()

            for item in self.techniques

        ]