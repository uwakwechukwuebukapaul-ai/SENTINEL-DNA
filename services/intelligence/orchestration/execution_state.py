"""
Execution State Tracking
"""


from datetime import datetime, timezone



class ExecutionState:


    def __init__(
        self,
        investigation_id: str,
    ):

        self.investigation_id = investigation_id

        self.status = "created"

        self.started_at = None

        self.completed_at = None



    def start(self):

        self.status = "running"

        self.started_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )



    def complete(self):

        self.status = "completed"

        self.completed_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )



    def to_dict(self):

        return {

            "investigation_id":
                self.investigation_id,

            "status":
                self.status,

            "started_at":
                self.started_at,

            "completed_at":
                self.completed_at,

        }