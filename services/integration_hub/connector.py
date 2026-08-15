from abc import ABC, abstractmethod
class ConnectorAdapter(ABC):
    def __init__(self, connector): self.connector = connector
    @abstractmethod
    def validate(self): ...
    def health_check(self): return {"status": "healthy", "message": "validated"}
    def receive(self, payload_reference): return payload_reference
    def send(self, payload_reference): return {"accepted": True, "payload_reference": payload_reference}
class SyntheticConnector(ConnectorAdapter):
    def validate(self): return bool(self.connector.provider and self.connector.connector_type)
