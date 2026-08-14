"""
Sentinel DNA
Database Models

Responsible for:
- Database schema creation
- Core data models
- Incident representation
"""

from datetime import datetime

from database.connection import database



# =====================================
# INCIDENT MODEL
# =====================================

class Incident:

    def __init__(
            self,
            incident_id,
            title,
            severity,
            threat=None,
            description="",
            status="OPEN",
            risk_score=0,
            **kwargs
    ):

        self.incident_id = incident_id

        self.title = title

        self.severity = severity

        self.threat = threat

        self.description = description

        self.status = status

        self.risk_score = risk_score

        self.created = datetime.now().isoformat()


        # Future SOC fields support
        for key, value in kwargs.items():

            setattr(self, key, value)



    def to_dict(self):

        data = {

            "incident_id": self.incident_id,

            "title": self.title,

            "severity": self.severity,

            "threat": self.threat,

            "description": self.description,

            "status": self.status,

            "risk_score": self.risk_score,

            "created": self.created

        }


        # Include additional fields

        for key, value in self.__dict__.items():

            if key not in data:

                data[key] = value


        return data



    def __repr__(self):

        return (

            f"<Incident "

            f"{self.incident_id} | "

            f"{self.severity} | "

            f"Risk:{self.risk_score}>"

        )





# =====================================
# DATABASE TABLE CREATION
# =====================================

def create_tables():

    with database.session() as conn:

        cursor = conn.cursor()



        # =====================================
        # CASES
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT UNIQUE NOT NULL,

            title TEXT NOT NULL,

            severity TEXT NOT NULL,

            description TEXT DEFAULT '',

            status TEXT DEFAULT 'OPEN',

            analyst TEXT DEFAULT '',

            created TEXT NOT NULL

        )
        """)



        # =====================================
        # CASE NOTES
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_notes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT NOT NULL,

            note TEXT NOT NULL,

            analyst TEXT DEFAULT '',

            created TEXT NOT NULL,

            FOREIGN KEY(case_id)
            REFERENCES cases(case_id)

        )
        """)



        # =====================================
        # EVIDENCE
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT NOT NULL,

            type TEXT NOT NULL,

            data TEXT NOT NULL,

            sha256 TEXT DEFAULT '',

            created TEXT NOT NULL,

            FOREIGN KEY(case_id)
            REFERENCES cases(case_id)

        )
        """)



        # =====================================
        # TIMELINE
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS timeline (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT NOT NULL,

            event_type TEXT NOT NULL,

            description TEXT NOT NULL,

            actor TEXT DEFAULT 'SYSTEM',

            created TEXT NOT NULL,

            FOREIGN KEY(case_id)
            REFERENCES cases(case_id)

        )
        """)



        # =====================================
        # IOCS
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS iocs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            ioc_id TEXT UNIQUE NOT NULL,

            case_id TEXT NOT NULL,

            ioc_type TEXT NOT NULL,

            value TEXT NOT NULL,

            confidence TEXT DEFAULT 'MEDIUM',

            reputation TEXT DEFAULT 'UNKNOWN',

            source TEXT DEFAULT 'LOCAL',

            created TEXT NOT NULL,

            FOREIGN KEY(case_id)
            REFERENCES cases(case_id)

        )
        """)



        # =====================================
        # INCIDENTS
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            incident_id TEXT UNIQUE NOT NULL,

            title TEXT NOT NULL,

            severity TEXT NOT NULL,

            threat TEXT DEFAULT '',

            description TEXT DEFAULT '',

            risk_score INTEGER DEFAULT 0,

            status TEXT DEFAULT 'OPEN',

            created TEXT NOT NULL

        )
        """)



        # =====================================
        # ANALYST ACTIONS
        # =====================================

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyst_actions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            case_id TEXT NOT NULL,

            action TEXT NOT NULL,

            analyst TEXT DEFAULT 'SYSTEM',

            created TEXT NOT NULL

        )
        """)



    return True





# =====================================
# DIRECT TEST
# =====================================

if __name__ == "__main__":


    print(
        "🧬 SENTINEL DNA DATABASE MODELS"
    )

    print("=" * 50)



    create_tables()



    incident = Incident(

        incident_id="INC-TEST001",

        title="Phishing Attack",

        severity="HIGH",

        threat="Credential Theft",

        description="Credential harvesting attempt detected",

        risk_score=95

    )


    print(
        incident.to_dict()
    )
