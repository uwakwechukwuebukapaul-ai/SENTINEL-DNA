from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any

from database.connection import DatabaseConnection, database_for_environment
from database.portability import table_columns
from database.ioc_repository import IOCRepository
from services.intelligence.ioc.persistence_service import IOCDataAccessService

from .dashboard_models import DashboardSnapshot


class DashboardService:
    """
    Bounded read-only SOC Command Center projection.

    Supports historical and current Sentinel DNA schemas.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
    ) -> None:
        self.db = DatabaseConnection(db_path) if db_path is not None else database_for_environment()
        self.db_path = str(getattr(self.db, "database_path", ""))
        self.iocs = IOCDataAccessService(IOCRepository(self.db))


    def _rows(
        self,
        conn,
        sql: str,
        params: tuple = (),
    ) -> list[dict[str, Any]]:

        return [
            dict(row)
            for row in conn.execute(
                sql,
                params
            ).fetchall()
        ]


    @staticmethod
    def _json(value: Any) -> list[str]:

        if isinstance(value, list):
            return [str(x) for x in value]

        if not value:
            return []

        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return [str(x) for x in parsed]

            return [str(parsed)]

        except Exception:
            return [str(value)]


    @staticmethod
    def _table_exists(
        conn,
        name: str,
    ) -> bool:

        return bool(table_columns(conn, getattr(conn, "backend_name", "sqlite"), name))


    @staticmethod
    def _columns(
        conn,
        table: str,
    ) -> set[str]:

        if not DashboardService._table_exists(conn, table):
            return set()

        return table_columns(conn, getattr(conn, "backend_name", "sqlite"), table)


    def snapshot(
        self,
        limit: int = 25,
    ) -> DashboardSnapshot:

        limit = max(
            1,
            min(
                int(limit),
                100
            )
        )


        with self.db.session() as conn:

            cases = self._rows(
                conn,
                """
                SELECT
                    case_id,
                    title,
                    severity,
                    status,
                    created
                FROM cases
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )


            metrics = self._rows(
                conn,
                """
                SELECT
                    COUNT(*) total_cases,

                    SUM(
                        CASE
                        WHEN UPPER(status)
                        IN
                        (
                            'OPEN',
                            'ACTIVE',
                            'INVESTIGATING',
                            'IN_PROGRESS'
                        )
                        THEN 1 ELSE 0 END
                    )
                    active_investigations,


                    SUM(
                        CASE
                        WHEN UPPER(severity)
                        IN
                        (
                            'CRITICAL',
                            'HIGH'
                        )
                        THEN 1 ELSE 0 END
                    )
                    critical_high_cases,


                    SUM(
                        CASE
                        WHEN UPPER(status)
                        IN
                        (
                            'COMPLETED',
                            'CLOSED',
                            'RESOLVED'
                        )
                        THEN 1 ELSE 0 END
                    )
                    completed_investigations

                FROM cases
                """
            )[0]


            for key in metrics:
                metrics[key] = metrics[key] or 0



            intel = self.iocs.dashboard_records(limit)



            timeline = self._rows(
                conn,
                """
                SELECT
                    case_id,
                    event_type,
                    description,
                    actor,
                    created
                FROM timeline
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )



            raw=[]

            if self._table_exists(
                conn,
                "intelligence"
            ):

                raw=self._rows(
                    conn,
                    """
                    SELECT
                        case_id,
                        data
                    FROM intelligence
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (limit,)
                )



        techniques = Counter()
        confidence=[]


        for case in cases:

            severity=str(
                case.get("severity")
            ).upper()


            case["risk_score"] = (
                100
                if severity=="CRITICAL"
                else 75
                if severity=="HIGH"
                else 25
            )


            case["confidence"]=case.get(
                "confidence",
                0
            )


            try:
                confidence.append(
                    float(
                        case["confidence"]
                    )
                )

            except Exception:
                pass


            case["mitre_techniques"]=self._json(
                case.get(
                    "mitre_techniques"
                )
            )


            techniques.update(
                case["mitre_techniques"]
            )



        metrics["average_confidence"]=(
            round(
                sum(confidence)/len(confidence),
                3
            )
            if confidence
            else 0
        )



        for item in raw:

            techniques.update(
                self._json(
                    item.get("data")
                )
            )



        return DashboardSnapshot(
            metrics,
            cases,
            intel,
            [
                {
                    "technique":k,
                    "frequency":v
                }
                for k,v in techniques.most_common()
            ],
            timeline
        )
