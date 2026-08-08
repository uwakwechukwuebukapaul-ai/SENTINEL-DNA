"""
Sentinel DNA Investigation Timeline Builder
"""

from .event import TimelineEvent


class TimelineBuilder:


    def __init__(self):

        self.events = []



    def add(
        self,
        name,
        description,
    ):

        self.events.append(

            TimelineEvent(
                name=name,
                description=description,
            )

        )



    def build(self):

        return self.events