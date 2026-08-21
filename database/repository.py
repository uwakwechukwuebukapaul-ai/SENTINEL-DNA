"""
Sentinel DNA
Database Repository Layer

Handles:
- Case creation
- Case retrieval
- Case updates
- Analyst assignment
- Notes
- Evidence tracking
- IOC tracking
- Timeline support
"""


from datetime import datetime
import hashlib

from database.connection import database



# =====================================
# HASH GENERATOR
# =====================================

def generate_sha256(data):

    return hashlib.sha256(
        str(data).encode()
    ).hexdigest()



# =====================================
# CASE MANAGEMENT
# =====================================

def create_case(case):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cases
            (
                case_id,
                title,
                severity,
                description,
                status,
                created
            )

            VALUES (?,?,?,?,?,?)
            """,
            (
                case["case_id"],
                case["title"],
                case["severity"],
                case["description"],
                "OPEN",
                datetime.now().isoformat()
            )
        )

        conn.commit()

    return case["case_id"]



def get_cases():

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM cases
            ORDER BY id DESC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]



def get_case(case_id):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM cases
            WHERE case_id=?
            """,
            (case_id,)
        )

        row = cursor.fetchone()

        return dict(row) if row else None



def update_case_status(case_id, status):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cases
            SET status=?
            WHERE case_id=?
            """,
            (
                status,
                case_id
            )
        )

        conn.commit()

    return True



def assign_analyst(case_id, analyst):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE cases
            SET analyst=?
            WHERE case_id=?
            """,
            (
                analyst,
                case_id
            )
        )

        conn.commit()

    return True



# =====================================
# NOTES
# =====================================

def add_note(case_id, note):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO case_notes
            (
                case_id,
                note,
                created
            )

            VALUES (?,?,?)
            """,
            (
                case_id,
                note,
                datetime.now().isoformat()
            )
        )

        conn.commit()

    return True



def get_notes(case_id):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM case_notes
            WHERE case_id=?
            ORDER BY id DESC
            """,
            (case_id,)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]



# =====================================
# EVIDENCE ENGINE
# =====================================

def add_evidence_record(
        case_id,
        evidence_type,
        evidence_data
):

    evidence_hash = generate_sha256(
        evidence_data
    )

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO evidence
            (
                case_id,
                type,
                data,
                sha256,
                created
            )

            VALUES (?,?,?,?,?)
            """,
            (
                case_id,
                evidence_type,
                evidence_data,
                evidence_hash,
                datetime.now().isoformat()
            )
        )

        conn.commit()

    return evidence_hash



def get_evidence(case_id=None):

    with database.session() as conn:

        cursor = conn.cursor()

        if case_id:

            cursor.execute(
                """
                SELECT *
                FROM evidence
                WHERE case_id=?
                ORDER BY id DESC
                """,
                (case_id,)
            )

        else:

            cursor.execute(
                """
                SELECT *
                FROM evidence
                ORDER BY id DESC
                """
            )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]



# =====================================
# IOC MANAGEMENT
# =====================================

def add_ioc(
        case_id,
        ioc_type,
        value,
        confidence="MEDIUM",
        reputation="UNKNOWN",
        source="LOCAL"
):
    # Compatibility entry point: canonical IOC persistence lives in the
    # dedicated repository to prevent SQL contract drift.
    from database.ioc_repository import repository as ioc_repository

    ioc_repository.create(
        case_id,
        ioc_type,
        value,
        confidence,
        reputation,
        source,
    )
    return True



def get_iocs(case_id=None):
    from database.ioc_repository import repository as ioc_repository

    return (
        ioc_repository.list_for_case(case_id)
        if case_id
        else ioc_repository.list_all()
    )



# =====================================
# TIMELINE
# =====================================

def add_timeline_event(
        case_id,
        event_type,
        description,
        actor
):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO timeline
            (
                case_id,
                event_type,
                description,
                actor,
                created
            )

            VALUES (?,?,?,?,?)
            """,
            (
                case_id,
                event_type,
                description,
                actor,
                datetime.now().isoformat()
            )
        )

        conn.commit()

    return True



def get_timeline(case_id):

    with database.session() as conn:

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM timeline
            WHERE case_id=?
            ORDER BY id DESC
            """,
            (case_id,)
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]
