"""
Playbook registry.
"""



class PlaybookRegistry:


    def __init__(self):

        self.playbooks = {}



    def register(
        self,
        playbook,
    ):

        self.playbooks[
            playbook.name
        ] = playbook



    def get(
        self,
        name,
    ):

        return self.playbooks.get(
            name
        )



    def list_all(self):

        return list(
            self.playbooks.values()
        )