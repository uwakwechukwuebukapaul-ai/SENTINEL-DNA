import base64, json
class CredentialReferenceStore:
    """Stores opaque references only; production deployments replace this with KMS."""
    def __init__(self): self._references = {}
    def put(self, connector_id, credentials):
        if not isinstance(credentials, dict): raise ValueError("credentials_must_be_mapping")
        reference = base64.urlsafe_b64encode(json.dumps(credentials, sort_keys=True).encode()).decode()
        self._references[connector_id] = reference; return {"connector_id": connector_id, "stored": True}
    def has(self, connector_id): return connector_id in self._references
    def public(self, connector_id): return {"connector_id": connector_id, "stored": self.has(connector_id)}
