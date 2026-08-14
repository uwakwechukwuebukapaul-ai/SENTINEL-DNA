from ..connector import BaseConnector
class SyntheticTicketConnector(BaseConnector):
    connector_name="synthetic_ticketing"; capabilities=("create_ticket_reference",)
    def create_ticket(self,summary): return {"ticket_reference":"SYNTH-1","summary":summary,"synthetic_only":True}
