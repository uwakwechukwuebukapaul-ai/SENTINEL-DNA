import sqlite3
import json
from datetime import datetime


DB_NAME = "soc.db"


# ===============================
# DATABASE CONNECTION
# ===============================

def get_connection():

    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    return conn



# ===============================
# CREATE TABLE
# ===============================

def create_database():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        time TEXT,

        threat TEXT,

        severity TEXT,

        risk_score INTEGER,

        mitre TEXT,

        response_status TEXT,

        status TEXT DEFAULT 'OPEN',

        evidence TEXT DEFAULT '',

        actions TEXT DEFAULT '[]',

        analyst TEXT DEFAULT '',

        notes TEXT DEFAULT ''

    )
    """)

    conn.commit()
    conn.close()



# ===============================
# SAVE INCIDENT FINAL FIX
# ===============================

def save_incident(*args, **kwargs):

    conn = get_connection()
    cursor = conn.cursor()


    # Dictionary input support

    if len(args) == 1 and isinstance(args[0], dict):

        incident = args[0]

        time = incident.get(
            "time",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        threat = incident.get(
            "threat",
            "Unknown"
        )

        severity = incident.get(
            "severity",
            "LOW"
        )

        risk_score = incident.get(
            "risk_score",
            0
        )

        mitre = incident.get(
            "mitre",
            "N/A"
        )

        response_status = incident.get(
            "response_status",
            "INVESTIGATION REQUIRED"
        )

        actions = incident.get(
            "actions",
            []
        )


    else:

        # soc_pipeline.py format:
        #
        # time
        # threat
        # severity
        # risk_score
        # mitre
        # response_status
        # actions


        time = args[0] if len(args) > 0 else datetime.now()

        threat = args[1] if len(args) > 1 else "Unknown"

        severity = args[2] if len(args) > 2 else "LOW"

        risk_score = args[3] if len(args) > 3 else 0

        mitre = args[4] if len(args) > 4 else "N/A"

        response_status = args[5] if len(args) > 5 else "INVESTIGATION REQUIRED"

        actions = args[6] if len(args) > 6 else []



    # Fix risk score type

    try:
        risk_score = int(risk_score)

    except:

        risk_score = 0



    # Fix actions storage

    if isinstance(actions, list):

        actions = json.dumps(actions)

    else:

        actions = str(actions)



    cursor.execute("""

    INSERT INTO incidents

    (

        time,

        threat,

        severity,

        risk_score,

        mitre,

        response_status,

        status,

        evidence,

        actions

    )

    VALUES (?,?,?,?,?,?,?,?,?)

    """,

    (

        str(time),

        str(threat),

        str(severity),

        risk_score,

        str(mitre),

        str(response_status),

        "OPEN",

        "",

        actions

    ))



    conn.commit()

    conn.close()

    return True




# ===============================
# GET INCIDENTS
# ===============================

def get_incidents():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM incidents
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()


    return [
        dict(row)
        for row in rows
    ]



# ===============================
# GET SINGLE INCIDENT
# ===============================

def get_incident(id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM incidents
        WHERE id=?
        """,
        (id,)
    )

    row = cursor.fetchone()

    conn.close()


    if row:

        return dict(row)

    return None




# ===============================
# DASHBOARD STATISTICS
# ===============================

def dashboard_stats():

    incidents = get_incidents()


    total = len(incidents)

    high = 0

    open_cases = 0

    risk_total = 0



    for incident in incidents:


        if str(
            incident["severity"]
        ).upper() == "HIGH":

            high += 1



        if incident["status"] != "RESOLVED":

            open_cases += 1



        try:

            risk_total += int(
                incident["risk_score"]
            )

        except:

            pass



    average = 0


    if total > 0:

        average = round(
            risk_total / total,
            2
        )


    return {

        "total": total,

        "high": high,

        "open": open_cases,

        "average_risk": average

    }




# ===============================
# UPDATE STATUS
# ===============================

def update_status(id, status):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

    UPDATE incidents

    SET status=?

    WHERE id=?

    """,

    (
        status,
        id
    ))


    conn.commit()

    conn.close()




# ===============================
# ASSIGN ANALYST
# ===============================

def assign_analyst(id, analyst):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

    UPDATE incidents

    SET analyst=?

    WHERE id=?

    """,

    (
        analyst,
        id
    ))


    conn.commit()

    conn.close()




# ===============================
# NOTES
# ===============================

def add_notes(id, notes):

    conn = get_connection()

    cursor = conn.cursor()


    cursor.execute("""

    UPDATE incidents

    SET notes=?

    WHERE id=?

    """,

    (
        notes,
        id
    ))


    conn.commit()

    conn.close()




# compatibility

def save_notes(id, notes):

    add_notes(
        id,
        notes
    )




# START DATABASE

create_database()