"""
Investigation report repository.

Responsible for:
- storing investigation reports
- converting domain objects into JSON-safe structures
- preserving compatibility with existing Sentinel DNA modules
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any
from .errors import RepositoryError


class InvestigationReportRepository:
    """
    Persistent abstraction for investigation reports.

    Legacy contract:
        InvestigationReportRepository.save()
        InvestigationReportRepository.get_all()
        InvestigationReportRepository.clear()

    Supports:
        - dataclasses
        - domain objects
        - dictionaries
        - lists
    """


    def __init__(self, db=None):
        if db is None:
            from database.connection import database as default_db
            db = default_db
        self.db = db
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_reports (
                    case_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )



    def _serialize(
        self,
        value: Any,
    ) -> Any:

        if value is None:
            return None


        if isinstance(
            value,
            (
                str,
                int,
                float,
                bool,
            ),
        ):
            return value


        if is_dataclass(value):

            return self._serialize(
                asdict(value)
            )


        if hasattr(
            value,
            "to_dict",
        ):

            return self._serialize(
                value.to_dict()
            )


        if hasattr(
            value,
            "__dict__",
        ):

            return {
                key: self._serialize(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }


        if isinstance(
            value,
            dict,
        ):

            return {
                str(key): self._serialize(item)
                for key, item in value.items()
            }


        if isinstance(
            value,
            (list, tuple, set),
        ):

            return [
                self._serialize(item)
                for item in value
            ]


        return str(value)



    def save(
        self,
        report: Any,
    ):

        payload = self._serialize(
            report
        )

        # Validate JSON compatibility
        encoded = json.dumps(
            payload
        )

        stored = json.loads(
            encoded
        )

        case_id = stored.get("case_id") if isinstance(stored, dict) else None
        if not case_id:
            raise RepositoryError("Investigation report case_id is required")

        try:
            now = datetime.now(timezone.utc).isoformat()
            with self.db.session() as connection:
                connection.execute(
                    """
                    INSERT INTO investigation_reports(case_id, report_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(case_id) DO UPDATE SET
                        report_json=excluded.report_json,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (str(case_id), json.dumps(stored), now, now),
                )
        except Exception as exc:
            raise RepositoryError("Unable to persist investigation report") from exc

        return stored



    def get_all(self):

        with self.db.session() as connection:
            rows = connection.execute(
                "SELECT report_json FROM investigation_reports ORDER BY updated_at, case_id"
            ).fetchall()
        return [json.loads(row["report_json"]) for row in rows]



    def all(self):

        return self.get_all()

    def get_by_case_id(self, case_id: str):
        """Return the most recently saved report for a case."""
        with self.db.session() as connection:
            row = connection.execute(
                "SELECT report_json FROM investigation_reports WHERE case_id=?",
                (case_id,),
            ).fetchone()
        return json.loads(row["report_json"]) if row else None



    def clear(self):

        with self.db.session() as connection:
            connection.execute("DELETE FROM investigation_reports")



# Backward compatibility
ReportRepository = InvestigationReportRepository
