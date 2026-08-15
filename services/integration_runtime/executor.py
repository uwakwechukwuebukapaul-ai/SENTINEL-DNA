from .runtime import ConnectorRuntime
class ConnectorExecutor:
    def __init__(self, runtime=None): self.runtime = runtime or ConnectorRuntime()
    def execute(self, adapter, operation, payload=None): return self.runtime.execute(adapter, operation, payload)
