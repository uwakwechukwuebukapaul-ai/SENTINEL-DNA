import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import re
from threading import Barrier, Event
from time import sleep

import pytest

from database.connection import database
from database.connection import DatabaseConnection
from database.errors import DatabaseError
from database.ioc_repository import (
    IOCDuplicateError,
    IOCRepository,
    IOCValidationError,
)
from database.repository import add_ioc
from services.cases.case_service import CaseService
from services.intelligence.ioc.persistence_service import (
    IOCAccessContext,
    IOCAccessDenied,
    IOCDataAccessService,
)


def test_add_ioc_writes_canonical_contract(tmp_path):
    database_path = tmp_path / "ioc-repository.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL
            );
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ioc_id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                ioc_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT DEFAULT 'MEDIUM',
                reputation TEXT DEFAULT 'UNKNOWN',
                source TEXT DEFAULT 'LOCAL',
                created TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(case_id)
            );
            INSERT INTO cases VALUES ('INC-001', 'IOC repository test');
            """
        )

    previous_path = database.database_path
    database.database_path = str(database_path)
    try:
        assert add_ioc(
            "INC-001",
            "DOMAIN",
            "evil.example",
            confidence="HIGH",
            reputation="MALICIOUS",
            source="TEST",
        ) is True
    finally:
        database.database_path = previous_path

    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT ioc_id, case_id, ioc_type, value,
                   confidence, reputation, source
            FROM iocs
            """
        ).fetchone()

    assert row[0].startswith("IOC-")
    assert row[1:] == (
        "INC-001",
        "DOMAIN",
        "evil.example",
        "HIGH",
        "MALICIOUS",
        "TEST",
    )


def _repository_database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE cases (case_id TEXT PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE iocs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ioc_id TEXT UNIQUE NOT NULL,
                case_id TEXT NOT NULL,
                ioc_type TEXT NOT NULL,
                value TEXT NOT NULL,
                confidence TEXT DEFAULT 'MEDIUM',
                reputation TEXT DEFAULT 'UNKNOWN',
                source TEXT DEFAULT 'LOCAL',
                created TEXT NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(case_id)
            );
            INSERT INTO cases VALUES ('INC-001', 'IOC repository test');
            """
        )


def test_canonical_repository_validates_and_controls_duplicates(tmp_path):
    path = tmp_path / "canonical-repository.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path))

    created = repo.create("INC-001", "DOMAIN", "evil.example")
    existing = repo.create(
        "INC-001", "DOMAIN", "evil.example", duplicate_policy="return_existing"
    )

    assert created["ioc_type"] == "DOMAIN"
    assert existing["ioc_id"] == created["ioc_id"]
    assert repo.get_by_ioc_id(created["ioc_id"])["value"] == "evil.example"
    assert repo.search_by_value("evil.example")[0]["ioc_id"] == created["ioc_id"]

    with pytest.raises(IOCDuplicateError):
        repo.create("INC-001", "DOMAIN", "evil.example", duplicate_policy="reject")
    with pytest.raises(IOCValidationError):
        repo.create("INC-001", "DOMAIN", "")

    repo.create(
        "INC-001", "DOMAIN", "evil.example", duplicate_policy="allow"
    )
    assert repo.count() == 2


def test_existing_allow_duplicates_are_preserved_and_latest_is_selected(tmp_path):
    path = tmp_path / "existing-duplicates.db"
    _repository_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO iocs (ioc_id,case_id,ioc_type,value,created) "
            "VALUES ('IOC-1','INC-001','DOMAIN','evil.example','first')"
        )
        connection.execute(
            "INSERT INTO iocs (ioc_id,case_id,ioc_type,value,created) "
            "VALUES ('IOC-2','INC-001','DOMAIN','evil.example','later')"
        )

    repo = IOCRepository(DatabaseConnection(path))
    existing = repo.create(
        "INC-001", "DOMAIN", "evil.example",
        duplicate_policy="return_existing",
    )

    assert existing["ioc_id"] == "IOC-2"
    assert repo.count() == 2


def test_concurrent_return_existing_converges_on_one_record(tmp_path):
    path = tmp_path / "concurrent-return-existing.db"
    _repository_database(path)
    barrier = Barrier(2)

    def create():
        barrier.wait()
        return IOCRepository(DatabaseConnection(path)).create(
            "INC-001", "DOMAIN", "raced.example",
            duplicate_policy="return_existing",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))

    assert results[0]["ioc_id"] == results[1]["ioc_id"]
    assert IOCRepository(DatabaseConnection(path)).count() == 1


def test_concurrent_reject_has_one_winner_and_one_duplicate(tmp_path):
    path = tmp_path / "concurrent-reject.db"
    _repository_database(path)
    barrier = Barrier(2)

    def create():
        barrier.wait()
        try:
            return IOCRepository(DatabaseConnection(path)).create(
                "INC-001", "DOMAIN", "raced.example",
                duplicate_policy="reject",
            )
        except IOCDuplicateError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: create(), range(2)))

    assert sum(result == "duplicate" for result in results) == 1
    assert IOCRepository(DatabaseConnection(path)).count() == 1


def test_lock_contention_returns_existing_after_writer_releases(tmp_path):
    path = tmp_path / "locked-return-existing.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path, busy_timeout_ms=1_000))
    created = repo.create("INC-001", "DOMAIN", "locked.example")
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = Event()

    def create():
        started.set()
        return repo.create(
            "INC-001", "DOMAIN", "locked.example",
            duplicate_policy="return_existing",
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(create)
            assert started.wait(timeout=1)
            sleep(0.1)
            assert not result.done()
            lock.commit()
            assert result.result(timeout=2)["ioc_id"] == created["ioc_id"]
    finally:
        lock.close()


def test_lock_contention_rejects_after_writer_releases(tmp_path):
    path = tmp_path / "locked-reject.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path, busy_timeout_ms=1_000))
    repo.create("INC-001", "DOMAIN", "locked.example")
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = Event()

    def create():
        started.set()
        return repo.create(
            "INC-001", "DOMAIN", "locked.example",
            duplicate_policy="reject",
        )

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(create)
            assert started.wait(timeout=1)
            sleep(0.1)
            assert not result.done()
            lock.commit()
            with pytest.raises(IOCDuplicateError):
                result.result(timeout=2)
    finally:
        lock.close()


def test_allow_creates_duplicate_after_lock_contention_resolves(tmp_path):
    path = tmp_path / "locked-allow.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path, busy_timeout_ms=1_000))
    repo.create("INC-001", "DOMAIN", "locked.example")
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")
    started = Event()

    def create():
        started.set()
        return repo.create("INC-001", "DOMAIN", "locked.example")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(create)
            assert started.wait(timeout=1)
            sleep(0.1)
            assert not result.done()
            lock.commit()
            result.result(timeout=2)
    finally:
        lock.close()

    assert repo.count() == 2


def test_exhausted_lock_budget_raises_normalized_database_error(tmp_path):
    path = tmp_path / "exhausted-lock-budget.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path, busy_timeout_ms=50))
    lock = sqlite3.connect(path, isolation_level=None)
    lock.execute("BEGIN IMMEDIATE")

    try:
        with pytest.raises(DatabaseError) as error:
            repo.create("INC-001", "DOMAIN", "locked.example")
    finally:
        lock.rollback()
        lock.close()

    assert isinstance(error.value.__cause__, sqlite3.OperationalError)
    assert "locked" in str(error.value.__cause__).lower()


def test_canonical_repository_rolls_back_failed_foreign_key_insert(tmp_path):
    path = tmp_path / "rollback-repository.db"
    _repository_database(path)
    repo = IOCRepository(DatabaseConnection(path))

    with pytest.raises(Exception):
        repo.create("MISSING-CASE", "DOMAIN", "evil.example")

    assert repo.list_all() == []
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name='ioc_duplicate_keys'"
        ).fetchone() is None


def test_ioc_service_requires_authoritative_case_assignment(tmp_path):
    path = tmp_path / "authorized-ioc.db"
    _repository_database(path)
    with sqlite3.connect(path) as connection:
        connection.execute("INSERT INTO cases VALUES ('INC-002', 'Other case')")

    db = DatabaseConnection(path)
    cases = CaseService(db)
    cases.assign("INC-001", 7, 1)
    repo = IOCRepository(db)
    record = repo.create("INC-001", "DOMAIN", "assigned.example")
    service = IOCDataAccessService(repo)

    access = cases.authorize("INC-001", 7, "analyst")
    context = IOCAccessContext.from_authorized_case(access)
    assert service.list_for_case("INC-001", context=context)[0]["ioc_id"] == record["ioc_id"]

    with pytest.raises(IOCAccessDenied):
        service.list_for_case("INC-001", context=None)
    with pytest.raises(IOCAccessDenied):
        service.list_for_case("INC-002", context=context)
    assert cases.authorize("INC-002", 7, "analyst") is None


def test_runtime_ioc_sql_is_centralized():
    repository_root = Path(__file__).resolve().parents[3]
    runtime_files = (
        repository_root / "dashboard" / "app.py",
        repository_root / "services" / "dashboard" / "dashboard_service.py",
        repository_root / "services" / "hunting" / "engine.py",
        repository_root / "services" / "intelligence" / "ioc" / "persistence_service.py",
    )
    direct_sql = re.compile(
        r"\b(?:FROM|INTO|UPDATE|JOIN)\s+iocs\b|\bDELETE\s+FROM\s+iocs\b",
        re.IGNORECASE,
    )
    legacy_sql = re.compile(
        r"iocs\.type|SELECT\s+type\s+FROM\s+iocs",
        re.IGNORECASE,
    )

    for path in runtime_files:
        source = path.read_text(encoding="utf-8")
        assert not direct_sql.search(source), path
        assert not legacy_sql.search(source), path
        assert "IOCAccessContext.for_cases(" not in source, path
