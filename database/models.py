"""Core incident model and normalized schema bootstrap compatibility API."""

from datetime import datetime

from database.connection import database
from database.schema import initialize_schema


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
        **kwargs,
    ):
        self.incident_id = incident_id
        self.title = title
        self.severity = severity
        self.threat = threat
        self.description = description
        self.status = status
        self.risk_score = risk_score
        self.created = datetime.now().isoformat()
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
            "created": self.created,
        }
        for key, value in self.__dict__.items():
            if key not in data:
                data[key] = value
        return data

    def __repr__(self):
        return f"<Incident {self.incident_id} | {self.severity} | Risk:{self.risk_score}>"


def create_tables():
    """Preserve the legacy bootstrap API while using the normalized schema."""

    initialize_schema(database)
    return True


if __name__ == "__main__":
    create_tables()
    print("Sentinel DNA database initialized")
    print(
        Incident(
            incident_id="INC-TEST001",
            title="Phishing Attack",
            severity="HIGH",
            threat="Credential Theft",
            description="Credential harvesting attempt detected",
            risk_score=95,
        ).to_dict()
    )
