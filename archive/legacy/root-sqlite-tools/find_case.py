import sqlite3
from pathlib import Path


case_id = "INC-20260731-1B5374"


for db in Path(".").rglob("*.db"):

    try:

        conn = sqlite3.connect(db)

        cursor = conn.cursor()


        cursor.execute(
            """
            SELECT name 
            FROM sqlite_master
            WHERE type='table'
            """
        )


        tables = [
            x[0] for x in cursor.fetchall()
        ]


        if "cases" in tables:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM cases
                """
            )

            count = cursor.fetchone()[0]


            cursor.execute(
                """
                SELECT *
                FROM cases
                WHERE case_id=?
                """,
                (case_id,)
            )


            result = cursor.fetchone()


            print("\nDATABASE:", db)

            print("CASE COUNT:", count)


            if result:
                print("FOUND CASE:", result)


        conn.close()


    except Exception:
        pass