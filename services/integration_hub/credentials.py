import secrets

class CredentialReferenceStore:
    """Track credential presence without retaining credential material.

    The credential payload is accepted for backwards-compatible registration,
    but is deliberately discarded. Runtime integrations must resolve an
    external vault/KMS reference; this process-local registry is not a secret
    store and never returns credential material.
    """
    def __init__(self): self._references = {}
    def put(self, connector_id, credentials):
        if not isinstance(credentials, dict): raise ValueError("credentials_must_be_mapping")
        self._references[connector_id] = secrets.token_urlsafe(32)
        return {"connector_id": connector_id, "stored": True}
    def has(self, connector_id): return connector_id in self._references
    def public(self, connector_id): return {"connector_id": connector_id, "stored": self.has(connector_id)}
