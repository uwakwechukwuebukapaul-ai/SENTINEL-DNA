"""Bounded SQLite-to-backend conversion for the normalized core tables."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .backend import DatabaseBackend
from .schema import normalized_table_names


CORE_TABLE_ORDER = tuple(name for name in normalized_table_names() if name != "schema_migrations")
CORE_REQUIRED_COLUMNS = {
    "cases": ("id", "case_id", "title", "severity", "created"),
    "case_notes": ("id", "case_id", "note", "created"),
    "evidence": ("id", "case_id", "type", "data", "sha256", "created"),
    "timeline": ("id", "case_id", "event_type", "description", "created"),
    "iocs": ("id", "ioc_id", "case_id", "ioc_type", "value", "created"),
    "incidents": ("id", "incident_id", "title", "severity", "created"),
    "analyst_actions": ("id", "case_id", "action", "created"),
}
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConversionError(RuntimeError):
    """Raised when source data cannot be safely mapped to the core schema."""


@dataclass(frozen=True)
class ConversionReport:
    source: str
    tables: tuple[str, ...]
    row_counts: dict[str, int]
    content_digest: str


def _quote(identifier: str) -> str:
    if not _IDENTIFIER.fullmatch(identifier):
        raise ConversionError("unsafe_identifier")
    return '"' + identifier + '"'


def convert_sqlite_core_data(source: str | Path, target: DatabaseBackend) -> ConversionReport:
    """Copy normalized core rows into an empty target without serializing rows."""

    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file() or source_path.is_symlink():
        raise ConversionError("source_database_invalid")

    source_connection = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
    source_connection.row_factory = sqlite3.Row
    row_counts: dict[str, int] = {}
    content_hasher = hashlib.sha256()
    try:
        source_tables = {
            str(row[0])
            for row in source_connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing_tables = [table for table in CORE_TABLE_ORDER if table not in source_tables]
        if missing_tables:
            raise ConversionError("source_tables_missing:" + ",".join(missing_tables))

        with target.session() as connection:
            for table in CORE_TABLE_ORDER:
                source_columns = [
                    str(row[1])
                    for row in source_connection.execute(
                        f"PRAGMA table_info({_quote(table)})"
                    ).fetchall()
                ]
                missing_columns = [
                    column
                    for column in CORE_REQUIRED_COLUMNS[table]
                    if column not in source_columns
                ]
                if missing_columns:
                    raise ConversionError(
                        f"source_schema_not_normalized:{table}:{','.join(missing_columns)}"
                    )
                columns = tuple(source_columns)
                rows = source_connection.execute(
                    f"SELECT {', '.join(_quote(column) for column in columns)} "
                    f"FROM {_quote(table)} ORDER BY {_quote(columns[0])}"
                ).fetchall()
                content_hasher.update(
                    json.dumps(
                        {"table": table, "columns": columns},
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
                placeholders = ", ".join("?" for _ in columns)
                insert = (
                    f"INSERT INTO {_quote(table)} "
                    f"({', '.join(_quote(column) for column in columns)}) "
                    f"VALUES ({placeholders})"
                )
                for row in rows:
                    values = tuple(row[column] for column in columns)
                    connection.execute(insert, values)
                    content_hasher.update(
                        json.dumps(values, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
                    )
                row_counts[table] = len(rows)
    finally:
        source_connection.close()

    return ConversionReport(
        source=str(source_path),
        tables=CORE_TABLE_ORDER,
        row_counts=row_counts,
        content_digest=content_hasher.hexdigest(),
    )


__all__ = ["ConversionError", "ConversionReport", "convert_sqlite_core_data"]
