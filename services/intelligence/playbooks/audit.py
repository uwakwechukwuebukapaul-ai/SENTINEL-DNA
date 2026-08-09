"""
Playbook execution audit storage.
"""

from datetime import datetime, timezone



class PlaybookAudit:

    def __init__(self):

        self.events = []


    def record(
        self,
        event: dict,
    ):

        event["timestamp"] = (
           datetime.now(timezone.utc)
.isoformat()
        )

        self.events.append(
            event
        )


    def history(self):

        return list(
            self.events
        )


    def clear(self):

        self.events.clear()