"""
Sentinel DNA

Analyst Actions Engine

Responsible for:
- Recording analyst activities
- Assigning cases
- Updating case status
- Adding investigation notes
- Connecting actions to timeline
"""


from datetime import datetime
import uuid
import sys
from pathlib import Path


# =====================================
# PROJECT PATH
# =====================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from database.connection import database
from database.portability import identity_primary_key
from cases.timeline import add_timeline_event



# =====================================
# ACTION ID
# =====================================

def generate_action_id():

    return (
        "ACT-"
        + uuid.uuid4().hex[:8].upper()
    )



# =====================================
# RECORD ANALYST ACTION
# =====================================

def record_action(
        case,
        action,
        analyst="SYSTEM"
):

    case_id = (
        case.get("case_id")
        if isinstance(case, dict)
        else case
    )


    event = {

        "action_id":
            generate_action_id(),

        "case_id":
            case_id,

        "action":
            action,

        "analyst":
            analyst,

        "created":
            datetime.now().isoformat()

    }


    with database.session() as conn:

        cursor = conn.cursor()


        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS analyst_actions (

                id {identity_primary_key(database.backend_name)},

                case_id TEXT NOT NULL,

                action TEXT NOT NULL,

                analyst TEXT DEFAULT 'SYSTEM',

                created TEXT NOT NULL

            )
            """
        )


        cursor.execute(
            """
            INSERT INTO analyst_actions
            (
                case_id,
                action,
                analyst,
                created
            )

            VALUES (?,?,?,?)

            """,

            (
                event["case_id"],
                event["action"],
                event["analyst"],
                event["created"]
            )

        )


    # Add to timeline

    add_timeline_event(

        case_id,

        "ANALYST_ACTION",

        action,

        analyst

    )


    return event



# =====================================
# ASSIGN ANALYST
# =====================================

def assign_analyst(
        case_id,
        analyst
):

    return record_action(

        case_id,

        f"Assigned case to {analyst}",

        analyst

    )



# =====================================
# UPDATE STATUS
# =====================================

def update_case_status(
        case_id,
        status,
        analyst="SYSTEM"
):

    return record_action(

        case_id,

        f"Case status changed to {status}",

        analyst

    )



# =====================================
# ADD NOTE
# =====================================

def add_note(

        case_id,

        note,

        analyst="SYSTEM"

):

    return record_action(

        case_id,

        f"Investigation note added: {note}",

        analyst

    )



# =====================================
# TEST
# =====================================

if __name__ == "__main__":


    print(
        "🧬 SENTINEL DNA ANALYST ACTION ENGINE"
    )

    print("=" * 50)


    test_case = {

        "case_id":
        "INC-20260731-TEST01"

    }


    action = record_action(

        test_case,

        "Reviewed phishing evidence",

        "SOC ANALYST"

    )


    print(action)
