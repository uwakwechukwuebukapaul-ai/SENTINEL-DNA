from __future__ import annotations

import json
import sqlite3

from collections import Counter
from pathlib import Path
from typing import Any

from .dashboard_models import DashboardSnapshot


class DashboardService:
    """
    Bounded read-only SOC Command Center projection.

    Supports historical and current Sentinel DNA schemas.
    """

    def __init__(
        self,
        db_path: str | Path = "soc.db",
    ) -> None:
        self.db_path = str(db_path)


    def _rows(
        self,
        conn: sqlite3.Connection,
        sql: str,
        params: tuple = (),
    ) -> list[dict[str, Any]]:

        conn.row_factory = sqlite3.Row

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
        conn: sqlite3.Connection,
        name: str,
    ) -> bool:

        return bool(
            conn.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table'
                AND name=?
                """,
                (name,)
            ).fetchone()
        )


    @staticmethod
    def _columns(
        conn: sqlite3.Connection,
        table: str,
    ) -> set[str]:

        if not DashboardService._table_exists(conn, table):
            return set()

        return {
            row[1]
            for row in conn.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }


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


        with sqlite3.connect(self.db_path) as conn:

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



            #
            # IOC compatibility layer
            #

            intel = []

            ioc_columns = self._columns(
                conn,
                "iocs"
            )


            if "iocs" in ioc_columns or self._table_exists(conn,"iocs"):

                if "ioc_type" in ioc_columns:

                    sql = """
                    SELECT
                        case_id,
                        ioc_type AS type,
                        value,
                        confidence AS risk_level,
                        created
                    FROM iocs
                    ORDER BY id DESC
                    LIMIT ?
                    """

                elif "type" in ioc_columns:

                    sql = """
                    SELECT
                        case_id,
                        type,
                        value,
                        NULL AS risk_level,
                        created
                    FROM iocs
                    ORDER BY id DESC
                    LIMIT ?
                    """

                else:

                    sql = """
                    SELECT
                        case_id,
                        'UNKNOWN' AS type,
                        value,
                        NULL AS risk_level,
                        created
                    FROM iocs
                    ORDER BY id DESC
                    LIMIT ?
                    """


                intel = self._rows(
                    conn,
                    sql,
                    (limit,)
                )



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
                    ORDER BY rowid DESC
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