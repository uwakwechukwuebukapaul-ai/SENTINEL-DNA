"""Repository-layer exception contracts."""

class RepositoryError(RuntimeError):
    """Stable persistence error independent of the storage backend."""
