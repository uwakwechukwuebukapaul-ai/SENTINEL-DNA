"""Database-layer exception contracts."""

class DatabaseError(RuntimeError):
    """Stable database abstraction error for backend-specific failures."""
