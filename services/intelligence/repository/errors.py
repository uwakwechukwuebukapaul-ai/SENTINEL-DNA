"""Repository-layer exception contracts."""

class RepositoryError(RuntimeError):
    """Stable persistence error independent of the storage backend."""


class ProviderObservationCursorError(RepositoryError):
    """Base class for bounded provider-observation cursor failures."""


class ProviderObservationCursorExpiredError(ProviderObservationCursorError):
    pass


class ProviderObservationCursorOrderingMismatchError(ProviderObservationCursorError):
    pass


class ProviderObservationCursorScopeMismatchError(ProviderObservationCursorError):
    pass


class ProviderObservationInvalidCursorSignatureError(ProviderObservationCursorError):
    pass


class ProviderObservationInvalidPageSizeError(ProviderObservationCursorError):
    pass


class ProviderObservationMalformedCursorError(ProviderObservationCursorError):
    pass


class ProviderObservationUnsupportedCursorVersionError(ProviderObservationCursorError):
    pass


class ProviderObservationProjectionBoundedError(RepositoryError):
    """A provider-observation projection exceeded its configured bound."""
