"""
Runtime Intelligence Registry

Dependency registry for intelligence components.
"""


class RuntimeIntelligenceRegistry:


    def __init__(self):

        self.components = {}



    def register(
        self,
        name: str,
        component,
    ):

        self.components[name] = component



    def get(
        self,
        name: str,
    ):

        return self.components.get(
            name
        )



    def available(
        self,
    ):

        return list(
            self.components.keys()
        )



    def remove(
        self,
        name: str,
    ):

        return self.components.pop(
            name,
            None,
        )