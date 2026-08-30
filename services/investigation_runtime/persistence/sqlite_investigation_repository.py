"""
SQLite investigation persistence.

Stores investigation state as JSON while keeping the
domain state model independent from SQLite.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from database.backend import DatabaseBackend
from database.connection import DatabaseConnection
from database.portability import table_columns

from ..state import (
    InvestigationState,
    InvestigationStatus,
)

from .investigation_repository import (
    InvestigationRepository,
)


class SQLiteInvestigationRepository(
    InvestigationRepository
):
    """
    Backend-neutral investigation repository with a retained legacy name.

    The repository owns its database connection lifecycle
    and initializes its schema automatically.
    """

    def __init__(
        self,
        database_path: str | Path | DatabaseBackend,
    ) -> None:
        self.db = (
            database_path
            if hasattr(database_path, "session")
            else DatabaseConnection(database_path)
        )
        self.database_path = getattr(self.db, "database_path", database_path)

        self._initialize()

    def _initialize(self) -> None:
        with self.db.session() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS
                investigations (
                    investigation_id TEXT PRIMARY KEY,
                    investigation_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT,
                    completed_stages_json TEXT NOT NULL DEFAULT '[]',
                    results_json TEXT NOT NULL DEFAULT '{}',
                    intelligence_json TEXT NOT NULL,
                    correlation_json TEXT NOT NULL,
                    confidence_json TEXT NOT NULL,
                    finding_json TEXT NOT NULL,
                    errors_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            columns = table_columns(
                connection,
                self.db.backend_name,
                "investigations",
            )
            additions = {
                "current_stage": "ALTER TABLE investigations ADD COLUMN current_stage TEXT",
                "completed_stages_json": "ALTER TABLE investigations ADD COLUMN completed_stages_json TEXT NOT NULL DEFAULT '[]'",
                "results_json": "ALTER TABLE investigations ADD COLUMN results_json TEXT NOT NULL DEFAULT '{}'",
                "metadata_json": "ALTER TABLE investigations ADD COLUMN metadata_json TEXT NOT NULL DEFAULT '{}'",
            }
            for column, statement in additions.items():
                if column not in columns:
                    connection.execute(statement)

            connection.commit()

    def create(
        self,
        state: InvestigationState,
    ) -> InvestigationState:
        if not isinstance(
            state,
            InvestigationState,
        ):
            raise TypeError(
                "State must be an InvestigationState."
            )

        if self.exists(
            state.investigation_id
        ):
            raise ValueError(
                f"Investigation "
                f"'{state.investigation_id}' "
                "already exists."
            )

        payload = state.to_dict()

        with self.db.session() as connection:
            connection.execute(
                """
                INSERT INTO investigations (
                    investigation_id,
                    investigation_json,
                    status,
                    current_stage,
                    completed_stages_json,
                    results_json,
                    intelligence_json,
                    correlation_json,
                    confidence_json,
                    finding_json,
                    errors_json,
                    metadata_json,
                    created_at,
                    started_at,
                    completed_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["investigation_id"],
                    self._encode(
                        payload["investigation"]
                    ),
                    payload["status"],
                    payload["current_stage"],
                    self._encode(payload["completed_stages"]),
                    self._encode(payload["results"]),
                    self._encode(
                        payload["intelligence"]
                    ),
                    self._encode(
                        payload["correlation"]
                    ),
                    self._encode(
                        payload["confidence"]
                    ),
                    self._encode(
                        payload["finding"]
                    ),
                    self._encode(
                        payload["errors"]
                    ),
                    self._encode(payload["metadata"]),
                    payload["created_at"],
                    payload["started_at"],
                    payload["completed_at"],
                    payload["updated_at"],
                ),
            )

            connection.commit()

        return state

    def get(
        self,
        investigation_id: str,
    ) -> InvestigationState:
        if not investigation_id:
            raise ValueError(
                "Investigation ID is required."
            )

        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM investigations
                WHERE investigation_id = ?
                """,
                (investigation_id,),
            ).fetchone()

        if row is None:
            raise KeyError(
                f"Investigation "
                f"'{investigation_id}' "
                "was not found."
            )

        return self._deserialize(row)

    def exists(
        self,
        investigation_id: str,
    ) -> bool:
        if not investigation_id:
            return False

        with self.db.session() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM investigations
                WHERE investigation_id = ?
                LIMIT 1
                """,
                (investigation_id,),
            ).fetchone()

        return row is not None

    def update(
        self,
        state: InvestigationState,
    ) -> InvestigationState:
        if not isinstance(
            state,
            InvestigationState,
        ):
            raise TypeError(
                "State must be an InvestigationState."
            )

        if not self.exists(
            state.investigation_id
        ):
            raise KeyError(
                f"Investigation "
                f"'{state.investigation_id}' "
                "was not found."
            )

        payload = state.to_dict()

        with self.db.session() as connection:
            connection.execute(
                """
                UPDATE investigations
                SET
                    investigation_json = ?,
                    status = ?,
                    current_stage = ?,
                    completed_stages_json = ?,
                    results_json = ?,
                    intelligence_json = ?,
                    correlation_json = ?,
                    confidence_json = ?,
                    finding_json = ?,
                    errors_json = ?,
                    metadata_json = ?,
                    created_at = ?,
                    started_at = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE investigation_id = ?
                """,
                (
                    self._encode(
                        payload["investigation"]
                    ),
                    payload["status"],
                    payload["current_stage"],
                    self._encode(payload["completed_stages"]),
                    self._encode(payload["results"]),
                    self._encode(
                        payload["intelligence"]
                    ),
                    self._encode(
                        payload["correlation"]
                    ),
                    self._encode(
                        payload["confidence"]
                    ),
                    self._encode(
                        payload["finding"]
                    ),
                    self._encode(
                        payload["errors"]
                    ),
                    self._encode(payload["metadata"]),
                    payload["created_at"],
                    payload["started_at"],
                    payload["completed_at"],
                    payload["updated_at"],
                    payload["investigation_id"],
                ),
            )

            connection.commit()

        return state

    def delete(
        self,
        investigation_id: str,
    ) -> InvestigationState:
        state = self.get(
            investigation_id
        )

        with self.db.session() as connection:
            connection.execute(
                """
                DELETE FROM investigations
                WHERE investigation_id = ?
                """,
                (investigation_id,),
            )

            connection.commit()

        return state

    def list(
        self,
    ) -> list[InvestigationState]:
        with self.db.session() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM investigations
                ORDER BY created_at ASC
                """
            ).fetchall()

        return [
            self._deserialize(row)
            for row in rows
        ]

    @staticmethod
    def _encode(
        value: Any,
    ) -> str:
        return json.dumps(
            value,
            separators=(",", ":"),
        )

    @staticmethod
    def _decode(
        value: str,
    ) -> Any:
        return json.loads(value)

    @classmethod
    def _deserialize(
        cls,
        row: Any,
    ) -> InvestigationState:
        state = InvestigationState(
            investigation_id=row[
                "investigation_id"
            ],
            investigation=cls._decode(
                row["investigation_json"]
            ),
            status=InvestigationStatus(
                row["status"]
            ),
            current_stage=row["current_stage"],
            completed_stages=cls._decode(row["completed_stages_json"] or "[]"),
            results=cls._decode(row["results_json"] or "{}"),
            intelligence=cls._decode(
                row["intelligence_json"]
            ),
            correlation=cls._decode(
                row["correlation_json"]
            ),
            confidence=cls._decode(
                row["confidence_json"]
            ),
            finding=cls._decode(
                row["finding_json"]
            ),
            errors=cls._decode(
                row["errors_json"]
            ),
            metadata=cls._decode(row["metadata_json"] or "{}"),
            created_at=datetime.fromisoformat(
                row["created_at"]
            ),
            started_at=(
                datetime.fromisoformat(
                    row["started_at"]
                )
                if row["started_at"]
                else None
            ),
            completed_at=(
                datetime.fromisoformat(
                    row["completed_at"]
                )
                if row["completed_at"]
                else None
            ),
            updated_at=datetime.fromisoformat(
                row["updated_at"]
            ),
        )

        return state
