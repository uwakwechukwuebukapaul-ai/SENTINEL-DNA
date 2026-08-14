"""
Sentinel DNA Report Repository

Stores generated investigation reports.
"""

from __future__ import annotations

from typing import Any


class ReportRepository:
    """
    Investigation report persistence repository.

    Current:
        In-memory storage.

    Future:
        Database-backed storage.
        Object storage.
        Enterprise report indexing.
    """

    def __init__(self) -> None:
        self._reports: dict[str, dict[str, Any]] = {}


    def save(
        self,
        case_id: str,
        report: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Store investigation report.
        """

        self._reports[case_id] = report

        return report


    def get(
        self,
        case_id: str,
    ) -> dict[str, Any] | None:
        """
        Retrieve report.
        """

        return self._reports.get(case_id)

    def get_by_case_id(self, case_id: str) -> dict[str, Any] | None:
        """Compatibility alias used by investigation consumers."""
        return self.get(case_id)


    def exists(
        self,
        case_id: str,
    ) -> bool:
        """
        Check report existence.
        """

        return case_id in self._reports


    def list_all(self) -> list[dict[str, Any]]:
        """
        Return all reports.
        """

        return list(self._reports.values())


    def delete(
        self,
        case_id: str,
    ) -> bool:
        """
        Remove report.
        """

        if case_id not in self._reports:
            return False

        del self._reports[case_id]

        return True


    def clear(self) -> None:
        """
        Remove all reports.
        """

        self._reports.clear()
