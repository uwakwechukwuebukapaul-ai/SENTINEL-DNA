"""
Investigation Memory Store

Stores learned investigation knowledge.
"""


class InvestigationMemory:


    def __init__(self):

        self.memory = []


    def store(
        self,
        investigation
    ):

        self.memory.append(
            investigation
        )


    def search(
        self,
        keyword
    ):

        results = []

        for item in self.memory:

            text = str(item).lower()

            if keyword.lower() in text:

                results.append(
                    item
                )

        return results


    def count(self):

        return len(
            self.memory
        )