"""
Sentinel DNA
IOC Repository

Handles:
- Save IOC
- Get IOC
- Search IOC
- Statistics
"""

import sys
from pathlib import Path
from datetime import datetime
import uuid
from typing import Any, Literal

# =====================================
# PROJECT PATH FIX
# =====================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database.connection import database
from database.repository import create_case


DuplicatePolicy = Literal["allow", "return_existing", "reject"]


class IOCValidationError(ValueError):
    """Raised when an IOC value violates the persistence contract."""


class IOCDuplicateError(ValueError):
    """Raised when duplicate creation is explicitly disallowed."""


# =====================================
# IOC ID
# =====================================

def generate_ioc_id():

    return "IOC-" + uuid.uuid4().hex[:8].upper()


class IOCRepository:
    """Canonical persistence boundary for the migrated ``iocs`` table.

    Authorization is deliberately handled by the application service layer;
    this class accepts only canonical database fields and uses the shared
    ``DatabaseConnection`` transaction boundary.
    """

    def __init__(self, connection=None):
        self.connection = connection or database

    @staticmethod
    def _required_text(name: str, value: Any, maximum: int) -> str:
        if not isinstance(value, str) or not value.strip():
            raise IOCValidationError(f"{name}_required")
        if len(value) > maximum:
            raise IOCValidationError(f"{name}_too_long")
        return value

    @staticmethod
    def _ensure_duplicate_registry(conn) -> None:
        """Create and seed the DB-backed identity registry when needed."""
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ioc_duplicate_keys (
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
        conn.execute(
            """
            INSERT OR REPLACE INTO ioc_duplicate_keys
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

    @staticmethod
    def _row_for_identity(conn, fields: tuple[str, str, str]):
        registry_row = conn.execute(
            """
            SELECT ioc_id
            FROM ioc_duplicate_keys
            WHERE case_id=? AND ioc_type=? AND value=?
            """,
            fields,
        ).fetchone()
        if registry_row:
            return conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs WHERE ioc_id=?
                """,
                (registry_row[0],),
            ).fetchone()
        return conn.execute(
            """
            SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                   reputation, source, created
            FROM iocs
            WHERE case_id=? AND ioc_type=? AND value=?
            ORDER BY id DESC LIMIT 1
            """,
            fields,
        ).fetchone()

    def create(
        self,
        case_id,
        ioc_type,
        value,
        confidence="MEDIUM",
        reputation="UNKNOWN",
        source="LOCAL",
        *,
        duplicate_policy: DuplicatePolicy = "allow",
    ) -> dict:
        fields = (
            self._required_text("case_id", case_id, 255),
            self._required_text("ioc_type", ioc_type, 128),
            self._required_text("value", value, 4096),
            self._required_text("confidence", confidence, 128),
            self._required_text("reputation", reputation, 128),
            self._required_text("source", source, 512),
        )
        if duplicate_policy not in {"allow", "return_existing", "reject"}:
            raise IOCValidationError("invalid_duplicate_policy")

        ioc_id = generate_ioc_id()
        created = datetime.now().isoformat()
        with self.connection.session() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._ensure_duplicate_registry(conn)

            existing = self._row_for_identity(conn, fields[:3])
            if existing and duplicate_policy == "return_existing":
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ioc_duplicate_keys
                        (case_id, ioc_type, value, ioc_id)
                    VALUES (?, ?, ?, ?)
                    """,
                    (*fields[:3], existing[1]),
                )
                return dict(existing)
            if existing and duplicate_policy == "reject":
                raise IOCDuplicateError("ioc_already_exists")

            cursor = conn.execute(
                """
                INSERT INTO iocs
                (ioc_id, case_id, ioc_type, value, confidence, reputation, source, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (ioc_id, *fields, created),
            )
            row = conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs WHERE id=?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            conn.execute(
                """
                INSERT OR REPLACE INTO ioc_duplicate_keys
                    (case_id, ioc_type, value, ioc_id)
                VALUES (?, ?, ?, ?)
                """,
                (*fields[:3], ioc_id),
            )
        return dict(row)

    def find_exact(self, case_id, ioc_type, value) -> dict | None:
        with self.connection.session() as conn:
            row = conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs
                WHERE case_id=? AND ioc_type=? AND value=?
                ORDER BY id DESC LIMIT 1
                """,
                (case_id, ioc_type, value),
            ).fetchone()
        return dict(row) if row else None

    def list_all(self, limit: int | None = None) -> list[dict]:
        sql = """
            SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                   reputation, source, created
            FROM iocs ORDER BY id DESC
        """
        params = ()
        if limit is not None:
            sql += " LIMIT ?"
            params = (max(1, min(int(limit), 1000)),)
        with self.connection.session() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def list_for_case(self, case_id) -> list[dict]:
        self._required_text("case_id", case_id, 255)
        with self.connection.session() as conn:
            rows = conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs WHERE case_id=? ORDER BY id DESC
                """,
                (case_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_by_ioc_id(self, ioc_id) -> dict | None:
        self._required_text("ioc_id", ioc_id, 255)
        with self.connection.session() as conn:
            row = conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs WHERE ioc_id=?
                """,
                (ioc_id,),
            ).fetchone()
        return dict(row) if row else None

    def search_by_value(self, value, limit: int = 100) -> list[dict]:
        self._required_text("value", value, 4096)
        with self.connection.session() as conn:
            rows = conn.execute(
                """
                SELECT id, ioc_id, case_id, ioc_type, value, confidence,
                       reputation, source, created
                FROM iocs WHERE value LIKE ? ORDER BY id DESC LIMIT ?
                """,
                (f"%{value}%", max(1, min(int(limit), 1000))),
            ).fetchall()
        return [dict(row) for row in rows]

    def count(self) -> int:
        with self.connection.session() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM iocs").fetchone()[0])

    def count_by_type(self) -> list[dict]:
        with self.connection.session() as conn:
            rows = conn.execute(
                """
                SELECT ioc_type, COUNT(*) AS total FROM iocs
                GROUP BY ioc_type ORDER BY total DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def count_by_reputation(self) -> list[dict]:
        with self.connection.session() as conn:
            rows = conn.execute(
                """
                SELECT reputation, COUNT(*) AS total FROM iocs
                GROUP BY reputation ORDER BY total DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]


repository = IOCRepository()


# =====================================
# SAVE IOC
# =====================================

def save_ioc(
    case_id,
    ioc_type,
    value,
    confidence="MEDIUM",
    reputation="UNKNOWN",
    source="LOCAL"
):
    """Compatibility API retaining the historical duplicate-allowing policy."""
    return repository.create(
        case_id, ioc_type, value, confidence, reputation, source
    )["ioc_id"]


# =====================================
# GET IOCS BY CASE
# =====================================

def get_iocs(case_id):
    return repository.list_for_case(case_id)


# =====================================
# GET ALL IOCS
# =====================================

def get_all_iocs():
    return repository.list_all()


# =====================================
# SEARCH IOC
# =====================================

def search_ioc(value):
    return repository.search_by_value(value)


# =====================================
# IOC COUNT
# =====================================

def count_iocs():
    return repository.count()


# =====================================
# IOC COUNT BY TYPE
# =====================================

def count_by_type():
    return repository.count_by_type()


# =====================================
# IOC COUNT BY REPUTATION
# =====================================

def count_by_reputation():
    return repository.count_by_reputation()


# =====================================
# TEST
# =====================================

if __name__ == "__main__":

    print("🧬 IOC REPOSITORY TEST")
    print("=" * 50)

    case_id = "INC-TEST-IOC"

    # Create test case if it doesn't exist
    try:

        create_case({

            "case_id": case_id,

            "title": "IOC Repository Test",

            "severity": "HIGH",

            "description": "Testing IOC Repository"

        })

    except Exception:
        # Ignore duplicate case_id
        pass

    save_ioc(
        case_id,
        "DOMAIN",
        "micr0soft-login.xyz",
        "HIGH",
        "SUSPICIOUS"
    )

    save_ioc(
        case_id,
        "URL",
        "https://micr0soft-login.xyz/login",
        "HIGH",
        "SUSPICIOUS"
    )

    save_ioc(
        case_id,
        "EMAIL",
        "admin@evil.xyz",
        "HIGH",
        "SUSPICIOUS"
    )

    print("\nIOC COUNT")
    print("-" * 40)
    print(count_iocs())

    print("\nCASE IOCS")
    print("-" * 40)

    for item in get_iocs(case_id):
        print(item)

    print("\nTYPE STATISTICS")
    print("-" * 40)

    for item in count_by_type():
        print(item)

    print("\nREPUTATION STATISTICS")
    print("-" * 40)

    for item in count_by_reputation():
        print(item)

    print("\n✅ IOC Repository test completed successfully.")
