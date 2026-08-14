class BaseConnector:
    connector_name="synthetic"; connector_version="1.0"; capabilities=()
    def connect(self): return {"connected":True,"synthetic_only":True}
    def disconnect(self): return {"disconnected":True}
    def health_check(self): return {"status":"healthy","synthetic_only":True}
    def send(self,payload): return {"accepted":True,"payload_reference":"synthetic","synthetic_only":True}
    def receive(self): return {"events":[],"synthetic_only":True}
