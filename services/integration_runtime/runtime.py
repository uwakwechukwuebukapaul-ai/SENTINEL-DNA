class ConnectorRuntime:
    """Small adapter contract; domain ingestion remains outside this runtime."""
    def execute(self, adapter, operation, payload=None):
        method = getattr(adapter, operation, None)
        if not callable(method): raise ValueError("unsupported_connector_operation")
        return method(payload) if payload is not None else method()
