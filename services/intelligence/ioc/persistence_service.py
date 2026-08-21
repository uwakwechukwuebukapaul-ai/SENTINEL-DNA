"""Application-level access boundary for persisted canonical IOCs.

This is intentionally separate from the IOC enrichment service in this package.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from database.ioc_repository import IOCRepository, repository
from services.cases.case_service import AuthorizedCaseAccess


class IOCAccessDenied(PermissionError):
    """Raised when an IOC read is outside the caller's case scope."""


@dataclass(frozen=True)
class IOCAccessContext:
    """Case capability supplied by an authorized application layer."""

    case_ids: frozenset[str]
    _authorization_token: object = field(
        default=None, repr=False, compare=False
    )

    @classmethod
    def from_authorized_case(
        cls, access: AuthorizedCaseAccess | None
    ) -> "IOCAccessContext":
        if access is None or not access.case_id or not access.user_id:
            raise IOCAccessDenied("authorized_case_required")
        return cls(frozenset({access.case_id}), _AUTHORIZATION_TOKEN)

    def permits(self, case_id: str) -> bool:
        return (
            self._authorization_token is _AUTHORIZATION_TOKEN
            and case_id in self.case_ids
        )


_AUTHORIZATION_TOKEN = object()


class IOCDataAccessService:
    """Canonical runtime IOC access with explicit case-scope enforcement."""

    def __init__(self, ioc_repository: IOCRepository | None = None) -> None:
        self.repository = ioc_repository or repository

    @staticmethod
    def _require_scope(case_id: str, context: IOCAccessContext | None) -> None:
        if context is None:
            raise IOCAccessDenied("ioc_access_context_required")
        if not context.permits(case_id):
            raise IOCAccessDenied("ioc_case_access_denied")

    def list_for_case(
        self, case_id: str, *, context: IOCAccessContext | None
    ) -> list[dict]:
        self._require_scope(case_id, context)
        return self.repository.list_for_case(case_id)

    def case_records(
        self, case_id: str, *, context: IOCAccessContext | None
    ) -> list[dict]:
        """Preserve the case API projection while retaining canonical fields."""
        return [
            {key: record[key] for key in (
                "id", "ioc_id", "ioc_type", "value", "confidence",
                "reputation", "source", "created"
            )}
            for record in self.list_for_case(case_id, context=context)
        ]

    def get_by_ioc_id(
        self, ioc_id: str, *, context: IOCAccessContext | None
    ) -> dict | None:
        record = self.repository.get_by_ioc_id(ioc_id)
        if record is not None:
            self._require_scope(record["case_id"], context)
        return record

    def list_recent(self, limit: int = 25) -> list[dict]:
        """Trusted server-side dashboard projection without a caller-selected case."""
        return self.repository.list_all(limit=limit)

    def count(self) -> int:
        return self.repository.count()

    def search_for_cases(
        self,
        value: str,
        *,
        context: IOCAccessContext | None,
        limit: int = 100,
    ) -> list[dict]:
        if context is None:
            raise IOCAccessDenied("ioc_access_context_required")
        return [
            record
            for record in self.repository.search_by_value(value, limit=limit)
            if context.permits(record["case_id"])
        ]

    def search_all(self, value: str, limit: int = 100) -> list[dict]:
        """Trusted internal search for callers already protected by RBAC."""
        return self.repository.search_by_value(value, limit=limit)

    def dashboard_records(self, limit: int = 25) -> list[dict]:
        """Explicitly map canonical persistence data to the dashboard DTO."""
        return [
            {
                "case_id": record["case_id"],
                "type": record["ioc_type"],
                "value": record["value"],
                "risk_level": record["confidence"],
                "created": record["created"],
            }
            for record in self.list_recent(limit)
        ]
