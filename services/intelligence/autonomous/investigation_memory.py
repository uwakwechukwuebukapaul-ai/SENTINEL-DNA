"""
Investigation Memory

Persistent runtime memory for autonomous investigations.
"""


class InvestigationMemory:


    def __init__(self):

        self._memory = []



    def add(
        self,
        investigation,
    ):

        self._memory.append(
            investigation
        )

        return investigation



    def store(
        self,
        investigation,
    ):

        return self.add(
            investigation
        )



    def get_all(self):

        return self._memory



    def get_history(self):

        return self._memory



    def clear(self):

        self._memory.clear()



    def count(self):

        return len(
            self._memory
        )