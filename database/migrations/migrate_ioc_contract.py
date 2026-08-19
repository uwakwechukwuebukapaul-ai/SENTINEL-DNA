"""
Sentinel DNA
IOC Contract Migration

Migrates the legacy IOC schema:

    id
    case_id
    type
    value
    created

to the canonical IOC schema:

    id
    ioc_id
    case_id
    ioc_type
    value
    confidence
    reputation
    source
    created

The migration is intentionally fail-closed and transactional.

Existing IOC records are preserved.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import resolve_database_path


# =====================================
# CONFIGURATION
# =====================================

DATABASE_PATH = resolve_database_path()

EXPECTED_LEGACY_COLUMNS = [
    "id",
    "case_id",
    "type",
    "value",
    "created",
]

CANONICAL_COLUMNS = [
    "id",
    "ioc_id",
    "case_id",
    "ioc_type",
    "value",
    "confidence",
    "reputation",
    "source",
    "created",
]

DUPLICATE_REGISTRY_TABLE = "ioc_duplicate_keys"


# =====================================
# LOGGING
# =====================================

def log(message: str) -> None:
    print(f"[IOC-MIGRATION] {message}")


# =====================================
# CONNECTION
# =====================================

def connect() -> sqlite3.Connection:
    if not DATABASE_PATH.exists():
        raise RuntimeError(
            f"Database does not exist: {DATABASE_PATH}"
        )

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys=ON")

    return connection


# =====================================
# SCHEMA HELPERS
# =====================================

def get_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


def table_exists(
    connection: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type='table'
        AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


# =====================================
# LEGACY SCHEMA VALIDATION
# =====================================

def validate_legacy_schema(
    connection: sqlite3.Connection,
) -> None:

    if not table_exists(connection, "iocs"):
        raise RuntimeError(
            "IOC table does not exist."
        )

    columns = get_columns(connection, "iocs")

    log(f"Existing IOC columns: {columns}")

    if columns == CANONICAL_COLUMNS:
        raise RuntimeError(
            "IOC table is already using the canonical schema. "
            "Migration is not required."
        )

    missing = [
        column
        for column in EXPECTED_LEGACY_COLUMNS
        if column not in columns
    ]

    if missing:
        raise RuntimeError(
            "Unexpected IOC schema. "
            f"Missing legacy columns: {missing}"
        )

    log("Legacy IOC schema validated.")


# =====================================
# DATA VALIDATION
# =====================================

def validate_legacy_data(
    connection: sqlite3.Connection,
) -> None:

    null_case_ids = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs
        WHERE case_id IS NULL
           OR TRIM(case_id) = ''
        """
    ).fetchone()[0]

    if null_case_ids:
        raise RuntimeError(
            f"Legacy IOC data contains {null_case_ids} "
            "NULL/empty case references."
        )

    null_values = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs
        WHERE value IS NULL
           OR TRIM(value) = ''
        """
    ).fetchone()[0]

    if null_values:
        raise RuntimeError(
            f"Legacy IOC data contains {null_values} "
            "NULL/empty IOC values."
        )

    orphan_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs AS i
        LEFT JOIN cases AS c
            ON c.case_id = i.case_id
        WHERE c.case_id IS NULL
        """
    ).fetchone()[0]

    if orphan_count:
        raise RuntimeError(
            f"Legacy IOC data contains {orphan_count} "
            "orphan case references."
        )

    log("Legacy IOC data validation passed.")


# =====================================
# CANONICAL TABLE
# =====================================

def create_canonical_table(
    connection: sqlite3.Connection,
) -> None:

    connection.execute(
        """
        CREATE TABLE iocs_new (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ioc_id TEXT UNIQUE NOT NULL,

            case_id TEXT NOT NULL,

            ioc_type TEXT NOT NULL,

            value TEXT NOT NULL,

            confidence TEXT DEFAULT 'MEDIUM',

            reputation TEXT DEFAULT 'UNKNOWN',

            source TEXT DEFAULT 'LEGACY_MIGRATION',

            created TEXT NOT NULL,

            FOREIGN KEY(case_id)
                REFERENCES cases(case_id)

        )
        """
    )

    log("Canonical IOC table created.")


# =====================================
# IOC ID GENERATION
# =====================================

def generate_migrated_ioc_id(
    legacy_id: int,
) -> str:

    namespace_value = (
        f"sentinel-dna:ioc:migration:{legacy_id}"
    )

    deterministic_uuid = uuid5(
        NAMESPACE_URL,
        namespace_value,
    )

    return (
        "IOC-MIGRATED-"
        + deterministic_uuid.hex[:12].upper()
    )


# =====================================
# DATA MIGRATION
# =====================================

def migrate_records(
    connection: sqlite3.Connection,
) -> tuple[int, int]:

    rows = connection.execute(
        """
        SELECT
            id,
            case_id,
            type,
            value,
            created
        FROM iocs
        ORDER BY id ASC
        """
    ).fetchall()

    migrated = 0

    for row in rows:

        ioc_id = generate_migrated_ioc_id(
            row["id"]
        )

        connection.execute(
            """
            INSERT INTO iocs_new
            (
                id,
                ioc_id,
                case_id,
                ioc_type,
                value,
                confidence,
                reputation,
                source,
                created
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                ioc_id,
                row["case_id"],
                row["type"],
                row["value"],
                "MEDIUM",
                "UNKNOWN",
                "LEGACY_MIGRATION",
                row["created"],
            ),
        )

        migrated += 1

    log(f"Migrated IOC records: {migrated}")

    return len(rows), migrated


# =====================================
# POST-MIGRATION VALIDATION
# =====================================

def validate_migrated_data(
    connection: sqlite3.Connection,
    expected_count: int,
) -> None:

    columns = get_columns(
        connection,
        "iocs_new",
    )

    if columns != CANONICAL_COLUMNS:
        raise RuntimeError(
            "Canonical IOC schema validation failed.\n"
            f"Expected: {CANONICAL_COLUMNS}\n"
            f"Actual:   {columns}"
        )

    actual_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs_new
        """
    ).fetchone()[0]

    if actual_count != expected_count:
        raise RuntimeError(
            "IOC row-count validation failed. "
            f"Expected {expected_count}, "
            f"got {actual_count}."
        )

    invalid_metadata = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs_new
        WHERE confidence IS NULL
           OR reputation IS NULL
           OR source IS NULL
        """
    ).fetchone()[0]

    if invalid_metadata:
        raise RuntimeError(
            "Migrated IOC metadata contains NULL values."
        )

    orphan_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs_new AS i
        LEFT JOIN cases AS c
            ON c.case_id = i.case_id
        WHERE c.case_id IS NULL
        """
    ).fetchone()[0]

    if orphan_count:
        raise RuntimeError(
            f"Migrated IOC table contains "
            f"{orphan_count} orphan references."
        )

    log("Migrated IOC data validation passed.")


# =====================================
# REPLACE TABLE
# =====================================

def replace_legacy_table(
    connection: sqlite3.Connection,
) -> None:

    connection.execute(
        """
        DROP TABLE iocs
        """
    )

    connection.execute(
        """
        ALTER TABLE iocs_new
        RENAME TO iocs
        """
    )

    log("Legacy IOC table replaced with canonical table.")


def ensure_duplicate_registry(
    connection: sqlite3.Connection,
) -> None:
    """Install the conditional uniqueness registry for canonical IOCs."""
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {DUPLICATE_REGISTRY_TABLE} (
            case_id TEXT NOT NULL,
            ioc_type TEXT NOT NULL,
            value TEXT NOT NULL,
            ioc_id TEXT NOT NULL UNIQUE,
            PRIMARY KEY (case_id, ioc_type, value),
            FOREIGN KEY (ioc_id) REFERENCES iocs(ioc_id)
                ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        f"""
        INSERT OR REPLACE INTO {DUPLICATE_REGISTRY_TABLE}
            (case_id, ioc_type, value, ioc_id)
        SELECT i.case_id, i.ioc_type, i.value, i.ioc_id
        FROM iocs AS i
        WHERE i.id = (
            SELECT MAX(latest.id)
            FROM iocs AS latest
            WHERE latest.case_id = i.case_id
              AND latest.ioc_type = i.ioc_type
              AND latest.value = i.value
        )
        """
    )


# =====================================
# FINAL VALIDATION
# =====================================

def final_validation(
    connection: sqlite3.Connection,
    expected_count: int,
) -> None:

    columns = get_columns(
        connection,
        "iocs",
    )

    if columns != CANONICAL_COLUMNS:
        raise RuntimeError(
            "Final IOC schema validation failed."
        )

    row_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs
        """
    ).fetchone()[0]

    if row_count != expected_count:
        raise RuntimeError(
            "Final IOC row count mismatch. "
            f"Expected {expected_count}, "
            f"got {row_count}."
        )

    orphan_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM iocs AS i
        LEFT JOIN cases AS c
            ON c.case_id = i.case_id
        WHERE c.case_id IS NULL
        """
    ).fetchone()[0]

    if orphan_count:
        raise RuntimeError(
            f"Final IOC table contains "
            f"{orphan_count} orphan references."
        )

    foreign_key_violations = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if foreign_key_violations:
        raise RuntimeError(
            "Final IOC table contains foreign-key violations."
        )

    foreign_keys = connection.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    if foreign_keys != 1:
        raise RuntimeError(
            "SQLite foreign-key enforcement is disabled."
        )

    registry_columns = get_columns(
        connection,
        DUPLICATE_REGISTRY_TABLE,
    )
    if registry_columns != [
        "case_id", "ioc_type", "value", "ioc_id"
    ]:
        raise RuntimeError("IOC duplicate registry validation failed.")

    registry_count = connection.execute(
        f"SELECT COUNT(*) FROM {DUPLICATE_REGISTRY_TABLE}"
    ).fetchone()[0]
    distinct_identity_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT case_id, ioc_type, value
            FROM iocs
            GROUP BY case_id, ioc_type, value
        )
        """
    ).fetchone()[0]
    if registry_count != distinct_identity_count:
        raise RuntimeError("IOC duplicate registry row count mismatch.")

    log("Final IOC contract validation passed.")


# =====================================
# MIGRATION
# =====================================

def migrate() -> None:

    log("=" * 60)
    log("Sentinel DNA IOC Contract Migration")
    log("=" * 60)

    log(f"Database: {DATABASE_PATH}")

    connection = connect()

    try:

        if (
            table_exists(connection, "iocs")
            and get_columns(connection, "iocs") == CANONICAL_COLUMNS
        ):
            canonical_count = connection.execute(
                "SELECT COUNT(*) FROM iocs"
            ).fetchone()[0]

            connection.execute("BEGIN")
            ensure_duplicate_registry(connection)
            final_validation(connection, canonical_count)
            connection.commit()

            log("IOC migration already complete; no changes made.")
            return

        validate_legacy_schema(connection)

        validate_legacy_data(connection)

        legacy_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM iocs
            """
        ).fetchone()[0]

        log(f"Legacy IOC count: {legacy_count}")

        connection.execute("BEGIN")

        create_canonical_table(connection)

        source_count, migrated_count = migrate_records(
            connection
        )

        if source_count != migrated_count:
            raise RuntimeError(
                "Migration count mismatch."
            )

        validate_migrated_data(
            connection,
            legacy_count,
        )

        replace_legacy_table(connection)

        ensure_duplicate_registry(connection)

        final_validation(
            connection,
            legacy_count,
        )

        connection.commit()

        log("=" * 60)
        log("IOC MIGRATION SUCCESS")
        log("=" * 60)
        log(f"Records preserved: {legacy_count}")
        log("Canonical schema installed: YES")
        log("Foreign keys enabled: YES")
        log("Orphan references: 0")

    except Exception:

        connection.rollback()

        log("=" * 60)
        log("IOC MIGRATION FAILED")
        log("=" * 60)
        log("Transaction rolled back.")
        log("The original IOC table was not committed to replacement.")

        raise

    finally:

        connection.close()


# =====================================
# ENTRY POINT
# =====================================

if __name__ == "__main__":
    migrate()
